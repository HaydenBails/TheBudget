"""HTTP contract tests for profile-isolated recurring-charge routes."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory, get_session
from app.main import app
from app.models import Base


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


def _profile(client: TestClient, name: str = "Personal") -> int:
    return client.post("/profiles", json={"name": name}).json()["id"]


def _account(client: TestClient, pid: int) -> int:
    return client.post(
        f"/profiles/{pid}/accounts",
        json={"issuer": "AMEX", "display_name": "Amex", "color": "#7c5cff"},
    ).json()["id"]


def _purchase(client: TestClient, pid: int, aid: int, day: str, merchant: str, cents: int) -> None:
    body = {
        "account_id": aid,
        "date": day,
        "raw_description": merchant,
        "merchant": merchant,
        "amount_cents": cents,
        "direction": "debit",
        "type": "purchase",
    }
    assert client.post(f"/profiles/{pid}/transactions", json=body).status_code == 201


def _seed_monthly(client: TestClient, pid: int, aid: int, merchant: str, cents: int) -> None:
    for month in (1, 2, 3, 4):
        _purchase(client, pid, aid, f"2026-0{month}-15", merchant, cents)


def test_detect_creates_series_and_links_transactions(api_client: TestClient) -> None:
    pid = _profile(api_client)
    aid = _account(api_client, pid)
    _seed_monthly(api_client, pid, aid, "NETFLIX", 2099)

    result = api_client.post(f"/profiles/{pid}/recurring/detect")
    assert result.status_code == 200
    body = result.json()
    assert body["created"] == 1
    assert body["detected"] == 1
    series = body["series"][0]
    assert series["cadence"] == "monthly"
    assert series["confidence"] == "high"
    assert series["status"] == "keep"
    assert series["occurrence_count"] == 4

    # Matched transactions are linked to the series.
    txns = api_client.get(f"/profiles/{pid}/transactions").json()
    linked = [t for t in txns if t.get("recurring_series_id") == series["id"]]
    assert len(linked) == 4


def test_detect_is_idempotent_and_preserves_user_decisions(api_client: TestClient) -> None:
    pid = _profile(api_client)
    aid = _account(api_client, pid)
    _seed_monthly(api_client, pid, aid, "SPOTIFY", 1099)

    first = api_client.post(f"/profiles/{pid}/recurring/detect").json()
    series_id = first["series"][0]["id"]
    # User cancels tracking for this series.
    patched = api_client.patch(
        f"/profiles/{pid}/recurring/{series_id}",
        json={"status": "cancel", "confirmed_by_user": True},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "cancel"

    second = api_client.post(f"/profiles/{pid}/recurring/detect").json()
    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["series"][0]["id"] == series_id
    assert second["series"][0]["status"] == "cancel"  # user decision preserved


def test_list_filters_by_status(api_client: TestClient) -> None:
    pid = _profile(api_client)
    aid = _account(api_client, pid)
    _seed_monthly(api_client, pid, aid, "NETFLIX", 2099)
    api_client.post(f"/profiles/{pid}/recurring/detect")

    kept = api_client.get(f"/profiles/{pid}/recurring", params={"status": "keep"})
    assert kept.status_code == 200
    assert len(kept.json()) == 1
    ignored = api_client.get(f"/profiles/{pid}/recurring", params={"status": "ignored"})
    assert ignored.json() == []


def test_delete_unlinks_transactions(api_client: TestClient) -> None:
    pid = _profile(api_client)
    aid = _account(api_client, pid)
    _seed_monthly(api_client, pid, aid, "NETFLIX", 2099)
    series_id = api_client.post(f"/profiles/{pid}/recurring/detect").json()["series"][0]["id"]

    assert api_client.delete(f"/profiles/{pid}/recurring/{series_id}").status_code == 204
    assert api_client.get(f"/profiles/{pid}/recurring/{series_id}").status_code == 404
    txns = api_client.get(f"/profiles/{pid}/transactions").json()
    assert all(t.get("recurring_series_id") is None for t in txns)


def test_cross_profile_series_is_not_found(api_client: TestClient) -> None:
    owner = _profile(api_client, "Owner")
    other = _profile(api_client, "Other")
    aid = _account(api_client, owner)
    _seed_monthly(api_client, owner, aid, "NETFLIX", 2099)
    series_id = api_client.post(f"/profiles/{owner}/recurring/detect").json()["series"][0]["id"]

    assert api_client.get(f"/profiles/{other}/recurring").json() == []
    assert api_client.get(f"/profiles/{other}/recurring/{series_id}").status_code == 404
    assert api_client.patch(
        f"/profiles/{other}/recurring/{series_id}", json={"status": "keep"}
    ).status_code == 404


def test_dining_noise_does_not_create_a_series(api_client: TestClient) -> None:
    pid = _profile(api_client)
    aid = _account(api_client, pid)
    for day, cents in [
        ("2026-06-01", 3200),
        ("2026-06-03", 1800),
        ("2026-06-04", 4500),
        ("2026-06-10", 2200),
        ("2026-06-11", 3900),
    ]:
        _purchase(api_client, pid, aid, day, "THE KEG", cents)
    result = api_client.post(f"/profiles/{pid}/recurring/detect").json()
    assert result["detected"] == 0
    assert result["series"] == []


def test_openapi_exposes_recurring_routes(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()
    assert "/profiles/{profile_id}/recurring" in schema["paths"]
    assert "/profiles/{profile_id}/recurring/detect" in schema["paths"]
    assert "/profiles/{profile_id}/recurring/{series_id}" in schema["paths"]


def test_transaction_read_exposes_recurring_series_id(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["TransactionRead"]["properties"]
    assert "recurring_series_id" in props
    # Sanity: a fresh purchase starts unlinked.
    pid = _profile(api_client)
    aid = _account(api_client, pid)
    _purchase(api_client, pid, aid, date(2026, 6, 1).isoformat(), "ONE OFF", 1000)
    txn = api_client.get(f"/profiles/{pid}/transactions").json()[0]
    assert txn["recurring_series_id"] is None
