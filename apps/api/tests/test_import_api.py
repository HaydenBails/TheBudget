"""BE-16 typed, profile-isolated import HTTP contract tests."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import load_or_create_import_fingerprint_key, settings
from app.db import create_db_engine, create_session_factory, get_session
from app.importing import DocumentLimits
from app.main import app
from app.middleware import ImportBodyLimitMiddleware
from app.models import Base
from app.routers.imports import (
    get_import_document_limits,
    get_import_fingerprint_key,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "fixtures" / "statements" / "td"
FINGERPRINT_KEY = b"api-test-local-fingerprint-key-material-32"


def test_fingerprint_key_is_stable_and_rejects_truncated_material(
    tmp_path: Path,
) -> None:
    key_path = tmp_path / "private" / "fingerprint.key"
    first = load_or_create_import_fingerprint_key(key_path)
    second = load_or_create_import_fingerprint_key(key_path)
    assert len(first) == 32
    assert first == second == key_path.read_bytes()

    truncated = tmp_path / "truncated.key"
    truncated.write_bytes(b"too-short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        load_or_create_import_fingerprint_key(truncated)

    generated = [
        load_or_create_import_fingerprint_key(tmp_path / "stress" / f"key-{index}")
        for index in range(64)
    ]
    assert all(len(key) == 32 for key in generated)


@pytest.fixture
def api_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    engine = create_db_engine(tmp_path / "import-api.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    temp_root = tmp_path / "statement-temp"
    monkeypatch.setattr(settings, "import_temp_root", temp_root)

    def override_session() -> Iterator[Session]:
        with session_factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_import_fingerprint_key] = lambda: FINGERPRINT_KEY
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_import_fingerprint_key, None)
        app.dependency_overrides.pop(get_import_document_limits, None)
        engine.dispose()


def _profile(client: TestClient, name: str = "Owner") -> int:
    response = client.post("/profiles", json={"name": name})
    assert response.status_code == 201
    return int(response.json()["id"])


def _account(client: TestClient, profile_id: int, name: str = "TD Visa") -> int:
    response = client.post(
        f"/profiles/{profile_id}/accounts",
        json={
            "issuer": "TD",
            "display_name": name,
            "color": "#12805c",
            "last4": "4821",
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _preview(
    client: TestClient,
    profile_id: int,
    account_id: int,
    *,
    fixture: str = "td_full_matrix.pdf",
    filename: str | None = None,
    content_type: str = "application/pdf",
):
    path = FIXTURE_ROOT / fixture
    return client.post(
        f"/profiles/{profile_id}/imports/preview",
        data={"account_id": str(account_id)},
        files={
            "statement": (
                filename or path.name,
                path.read_bytes(),
                content_type,
            )
        },
    )


def test_preview_get_commit_and_privacy_safe_openapi(api_client: TestClient) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)

    response = _preview(api_client, profile_id, account_id)
    assert response.status_code == 201, response.text
    preview = response.json()
    assert preview["account_id"] == preview["suggested_account_id"] == account_id
    assert preview["issuer"] == "TD"
    assert preview["transaction_count"] == 8
    assert len(preview["staged_transactions"]) == 8
    assert preview["parsed_total_cents"] == -3900
    assert preview["reconciliation_delta_cents"] == 0
    assert "file_sha256" not in preview
    assert "logical_statement_key" not in preview
    assert "transaction_fingerprint" not in preview["staged_transactions"][0]
    assert "pages" not in preview

    import_id = int(preview["id"])
    detail = api_client.get(f"/profiles/{profile_id}/imports/{import_id}")
    assert detail.status_code == 200
    assert detail.json()["staged_transactions"] == preview["staged_transactions"]
    assert "suggested_account_id" not in detail.json()

    committed = api_client.post(
        f"/profiles/{profile_id}/imports/{import_id}/commit",
        json={"acknowledge_needs_review": False},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert committed.json()["created_count"] == 8
    assert len(committed.json()["transaction_ids"]) == 8
    repeated_commit = api_client.post(
        f"/profiles/{profile_id}/imports/{import_id}/commit",
        json={"acknowledge_needs_review": False},
    )
    assert repeated_commit.status_code == 200
    assert repeated_commit.json() == committed.json()
    transactions = api_client.get(f"/profiles/{profile_id}/transactions")
    assert transactions.status_code == 200
    assert len(transactions.json()) == 8
    assert all(item["source"] == "pdf_import" for item in transactions.json())
    assert all(item["import_id"] == import_id for item in transactions.json())

    openapi = api_client.get("/openapi.json").json()
    import_paths = {
        path for path in openapi["paths"] if "/imports" in path
    }
    assert import_paths == {
        "/profiles/{profile_id}/imports/preview",
        "/profiles/{profile_id}/imports/{import_id}",
        "/profiles/{profile_id}/imports/{import_id}/commit",
        "/profiles/{profile_id}/imports/{import_id}/cancel",
    }
    schemas = openapi["components"]["schemas"]
    assert "file_sha256" not in schemas["ImportDetailResponse"]["properties"]
    assert "transaction_fingerprint" not in schemas["ImportCandidateResponse"][
        "properties"
    ]
    preview_body = openapi["paths"]["/profiles/{profile_id}/imports/preview"][
        "post"
    ]["requestBody"]
    assert preview_body["content"]["multipart/form-data"]
    for path in import_paths:
        for operation in openapi["paths"][path].values():
            assert "404" in operation["responses"]


def test_upload_boundaries_and_readable_document_errors(api_client: TestClient) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)

    wrong_extension = _preview(
        api_client,
        profile_id,
        account_id,
        filename="statement.txt",
    )
    assert (wrong_extension.status_code, wrong_extension.json()["code"]) == (
        415,
        "unsupported_document",
    )
    wrong_mime = _preview(
        api_client,
        profile_id,
        account_id,
        content_type="text/plain",
    )
    assert wrong_mime.status_code == 415
    not_pdf = api_client.post(
        f"/profiles/{profile_id}/imports/preview",
        data={"account_id": account_id},
        files={"statement": ("statement.pdf", b"not a pdf", "application/pdf")},
    )
    assert not_pdf.status_code == 415

    scanned = _preview(
        api_client,
        profile_id,
        account_id,
        fixture="td_scanned_placeholder.pdf",
    )
    assert scanned.status_code == 422
    assert scanned.json()["code"] == "scanned_document"
    assert "text-based PDF" in scanned.json()["detail"]
    unsupported = _preview(
        api_client,
        profile_id,
        account_id,
        fixture="td_unsupported_layout.pdf",
    )
    assert unsupported.status_code == 422
    assert "layout is not supported" in unsupported.json()["detail"]

    app.dependency_overrides[get_import_document_limits] = lambda: DocumentLimits(
        max_bytes=32,
        max_pages=20,
        max_extracted_chars=2_000_000,
        extraction_timeout_seconds=15,
    )
    oversized = _preview(api_client, profile_id, account_id)
    assert (oversized.status_code, oversized.json()["code"]) == (
        413,
        "document_too_large",
    )
    temp_root = settings.import_temp_root
    assert temp_root is not None
    assert list(temp_root.iterdir()) == []

    multiple = api_client.post(
        f"/profiles/{profile_id}/imports/preview",
        data={"account_id": account_id},
        files=[
            ("statement", ("one.pdf", b"%PDF-one", "application/pdf")),
            ("statement", ("two.pdf", b"%PDF-two", "application/pdf")),
        ],
    )
    assert multiple.status_code == 422


def test_http_body_limit_rejects_before_consuming_complete_stream(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)
    monkeypatch.setattr(settings, "import_max_bytes", 32)
    monkeypatch.setattr(settings, "import_multipart_overhead_bytes", 64)
    preflight = api_client.post(
        f"/profiles/{profile_id}/imports/preview",
        data={"account_id": account_id},
        files={
            "statement": (
                "statement.pdf",
                b"%PDF-" + b"x" * 1000,
                "application/pdf",
            )
        },
    )
    assert (preflight.status_code, preflight.json()["code"]) == (
        413,
        "request_body_too_large",
    )
    cors_preflight = api_client.post(
        f"/profiles/{profile_id}/imports/preview",
        headers={"Origin": "http://127.0.0.1:5173"},
        data={"account_id": account_id},
        files={
            "statement": (
                "statement.pdf",
                b"%PDF-" + b"x" * 1000,
                "application/pdf",
            )
        },
    )
    assert cors_preflight.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5173"
    )

    calls = 0
    sent: list[dict[str, object]] = []
    chunks = [b"a" * 40, b"b" * 40, b"c" * 40]

    async def downstream(scope, receive, send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        nonlocal calls
        body = chunks[calls]
        calls += 1
        return {
            "type": "http.request",
            "body": body,
            "more_body": calls < len(chunks),
        }

    async def send(message):
        sent.append(message)

    middleware = ImportBodyLimitMiddleware(downstream, max_body_bytes=64)
    asyncio.run(
        middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/profiles/1/imports/preview",
                "headers": [],
            },
            receive,
            send,
        )
    )
    assert calls == 2
    assert sent[0]["status"] == 413


def test_duplicate_conflict_persists_reference_and_cancel_is_idempotent(
    api_client: TestClient,
) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)
    first = _preview(api_client, profile_id, account_id)
    assert first.status_code == 201

    duplicate = _preview(api_client, profile_id, account_id)
    assert duplicate.status_code == 409
    body = duplicate.json()
    assert body["code"] == "blocked_file_hash"
    assert body["duplicate_of_import_id"] == first.json()["id"]
    assert body["import_id"] != first.json()["id"]
    persisted = api_client.get(
        f"/profiles/{profile_id}/imports/{body['import_id']}"
    )
    assert persisted.status_code == 200
    assert persisted.json()["duplicate_of_import_id"] == first.json()["id"]

    import_id = int(first.json()["id"])
    cancelled = api_client.post(
        f"/profiles/{profile_id}/imports/{import_id}/cancel"
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    repeated = api_client.post(
        f"/profiles/{profile_id}/imports/{import_id}/cancel"
    )
    assert repeated.status_code == 200
    assert api_client.get(
        f"/profiles/{profile_id}/imports/{import_id}"
    ).json()["staged_transactions"] == []

    committed_preview = _preview(api_client, profile_id, account_id)
    assert committed_preview.status_code == 201
    committed_id = int(committed_preview.json()["id"])
    assert api_client.post(
        f"/profiles/{profile_id}/imports/{committed_id}/commit",
        json={"acknowledge_needs_review": False},
    ).status_code == 200
    cannot_cancel = api_client.post(
        f"/profiles/{profile_id}/imports/{committed_id}/cancel"
    )
    assert cannot_cancel.status_code == 409


def test_needs_review_requires_acknowledgement(api_client: TestClient) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)
    manual = api_client.post(
        f"/profiles/{profile_id}/transactions",
        json={
            "account_id": account_id,
            "date": "2026-06-02",
            "posted_date": "2026-06-03",
            "raw_description": "synthetic   market",
            "amount_cents": 123456,
            "direction": "debit",
            "type": "purchase",
        },
    )
    assert manual.status_code == 201
    preview = _preview(api_client, profile_id, account_id)
    assert preview.status_code == 201
    assert preview.json()["validation_status"] == "needs_review"
    import_id = int(preview.json()["id"])

    rejected = api_client.post(
        f"/profiles/{profile_id}/imports/{import_id}/commit",
        json={"acknowledge_needs_review": False},
    )
    assert (rejected.status_code, rejected.json()["code"]) == (
        409,
        "acknowledgement_required",
    )
    accepted = api_client.post(
        f"/profiles/{profile_id}/imports/{import_id}/commit",
        json={"acknowledge_needs_review": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["created_count"] == 8


def test_cross_profile_import_ids_are_uniform_404(api_client: TestClient) -> None:
    owner = _profile(api_client)
    owner_account = _account(api_client, owner)
    other = _profile(api_client, "Other")
    _account(api_client, other, "Other card")
    preview = _preview(api_client, owner, owner_account)
    import_id = int(preview.json()["id"])

    for method, suffix, json in (
        ("get", "", None),
        ("post", "/commit", {"acknowledge_needs_review": False}),
        ("post", "/cancel", None),
    ):
        response = api_client.request(
            method,
            f"/profiles/{other}/imports/{import_id}{suffix}",
            json=json,
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "import not found"}


def test_malicious_filename_is_sanitized_and_temp_storage_is_empty(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)
    with caplog.at_level("INFO", logger="spending_tracker.imports"):
        response = _preview(
            api_client,
            profile_id,
            account_id,
            filename="../private/evil\u202e123456789.pdf",
        )
    assert response.status_code == 201
    source_name = response.json()["source_filename"]
    assert "/" not in source_name and "\\" not in source_name
    assert "123456789" not in source_name
    assert "\u202e" not in source_name
    assert "SYNTHETIC MARKET" not in caplog.text
    assert "evil" not in caplog.text
    temp_root = settings.import_temp_root
    assert temp_root is not None
    assert list(temp_root.iterdir()) == []


def test_database_commit_failure_returns_500_and_durably_persists_failed_state(
    api_client: TestClient,
) -> None:
    profile_id = _profile(api_client)
    account_id = _account(api_client, profile_id)
    preview = _preview(api_client, profile_id, account_id)
    import_id = int(preview.json()["id"])

    with patch(
        "app.services.imports.create_imported_transaction",
        side_effect=RuntimeError("synthetic database failure"),
    ):
        failed = api_client.post(
            f"/profiles/{profile_id}/imports/{import_id}/commit",
            json={"acknowledge_needs_review": False},
        )
    assert failed.status_code == 500
    assert failed.json() == {
        "detail": "import commit failed",
        "code": "commit_failed",
        "import_id": import_id,
        "duplicate_of_import_id": None,
        "status": "failed",
    }
    detail = api_client.get(f"/profiles/{profile_id}/imports/{import_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "failed"
    transactions = api_client.get(f"/profiles/{profile_id}/transactions")
    assert transactions.status_code == 200
    assert transactions.json() == []
