"""HTTP contract test: importing an Amex .xlsx workbook via the preview API."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory, get_session
from app.main import app
from app.models import Base

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXTURE = REPOSITORY_ROOT / "fixtures" / "statements" / "amex" / "amex_excel_matrix.xlsx"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_db_engine(tmp_path / "api.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    def override_session() -> Iterator[Session]:
        with session_factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


def _profile_and_account(client: TestClient) -> tuple[int, int]:
    pid = client.post("/profiles", json={"name": "Hayden"}).json()["id"]
    aid = client.post(
        f"/profiles/{pid}/accounts",
        json={"issuer": "AMEX", "display_name": "Amex", "color": "#7c5cff"},
    ).json()["id"]
    return pid, aid


def _preview(client: TestClient, pid: int, aid: int, filename: str = "amex.xlsx"):
    with FIXTURE.open("rb") as stream:
        return client.post(
            f"/profiles/{pid}/imports/preview",
            files={"statement": (filename, stream, XLSX_MIME)},
            data={"account_id": str(aid)},
        )


def test_excel_preview_uses_excel_parser_and_reconciles(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    response = _preview(api_client, pid, aid)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parser_name"] == "amex_excel"
    assert body["issuer"] == "AMEX"
    assert body["transaction_count"] == 7
    assert body["reconciliation_delta_cents"] == 0
    assert body["validation_status"] == "validated"
    # Charges are debits; the payment + refund are credits.
    assert body["payment_count"] == 1
    assert body["credit_count"] == 1


def test_excel_preview_commits_into_the_ledger(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    import_id = _preview(api_client, pid, aid).json()["id"]
    committed = api_client.post(f"/profiles/{pid}/imports/{import_id}/commit", json={})
    assert committed.status_code == 200, committed.text
    txns = api_client.get(f"/profiles/{pid}/transactions").json()
    assert len(txns) == 7
    fx = [t for t in txns if t["original_foreign_currency"] == "EUR"]
    assert len(fx) == 1 and fx[0]["original_foreign_amount_cents"] == 1000


def test_reimporting_same_workbook_is_blocked_as_duplicate(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    first = _preview(api_client, pid, aid)
    assert first.status_code == 201
    duplicate = _preview(api_client, pid, aid)
    assert duplicate.status_code == 409


def test_pdf_still_routes_to_a_pdf_parser(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    td_pdf = REPOSITORY_ROOT / "fixtures" / "statements" / "td" / "td_full_matrix.pdf"
    with td_pdf.open("rb") as stream:
        response = api_client.post(
            f"/profiles/{pid}/imports/preview",
            files={"statement": ("td.pdf", stream, "application/pdf")},
            data={"account_id": str(aid)},
        )
    assert response.status_code == 201, response.text
    assert response.json()["parser_name"] == "td_credit_card"
