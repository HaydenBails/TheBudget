"""HTTP contract tests for profile-isolated income-schedule routes."""

from __future__ import annotations

from collections.abc import Iterator
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


def _schedule(client: TestClient, pid: int, **kw: object) -> dict:
    body = {
        "name": "Paycheck",
        "amount_cents": 420000,
        "frequency": "biweekly",
        "start_date": "2026-06-05",
    }
    body.update(kw)
    response = client.post(f"/profiles/{pid}/income", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_next_expected(api_client: TestClient) -> None:
    pid = _profile(api_client)
    body = _schedule(api_client, pid)
    assert body["amount_cents"] == 420000
    assert body["frequency"] == "biweekly"
    assert body["is_active"] is True
    assert body["next_expected_date"] is not None


def test_occurrences_endpoint_forecasts_a_month(api_client: TestClient) -> None:
    pid = _profile(api_client)
    _schedule(api_client, pid, frequency="biweekly", start_date="2026-06-05")
    resp = api_client.get(
        f"/profiles/{pid}/income/occurrences",
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    assert resp.status_code == 200
    dates = [o["occurrence_date"] for o in resp.json()]
    assert dates == ["2026-06-05", "2026-06-19"]


def test_summary_reports_expected_income(api_client: TestClient) -> None:
    pid = _profile(api_client)
    _schedule(api_client, pid, frequency="monthly", start_date="2026-06-15", amount_cents=500000)
    resp = api_client.get(
        f"/profiles/{pid}/income/summary",
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["expected_cents"] == 500000
    assert len(body["occurrences"]) == 1


def test_paused_schedule_excluded_from_forecast(api_client: TestClient) -> None:
    pid = _profile(api_client)
    s = _schedule(api_client, pid, frequency="weekly", start_date="2026-06-01")
    api_client.patch(f"/profiles/{pid}/income/{s['id']}", json={"is_active": False})
    resp = api_client.get(
        f"/profiles/{pid}/income/occurrences",
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    assert resp.json() == []


def test_update_and_delete(api_client: TestClient) -> None:
    pid = _profile(api_client)
    s = _schedule(api_client, pid)
    updated = api_client.patch(
        f"/profiles/{pid}/income/{s['id']}", json={"amount_cents": 450000, "name": "Salary"}
    )
    assert updated.status_code == 200
    assert updated.json()["amount_cents"] == 450000
    assert updated.json()["name"] == "Salary"
    assert api_client.delete(f"/profiles/{pid}/income/{s['id']}").status_code == 204
    assert api_client.get(f"/profiles/{pid}/income/{s['id']}").status_code == 404


def test_end_before_start_is_rejected(api_client: TestClient) -> None:
    pid = _profile(api_client)
    response = api_client.post(
        f"/profiles/{pid}/income",
        json={
            "name": "Bad",
            "amount_cents": 1000,
            "frequency": "monthly",
            "start_date": "2026-06-30",
            "end_date": "2026-06-01",
        },
    )
    assert response.status_code == 422


def test_non_positive_amount_is_rejected(api_client: TestClient) -> None:
    pid = _profile(api_client)
    response = api_client.post(
        f"/profiles/{pid}/income",
        json={
            "name": "Zero",
            "amount_cents": 0,
            "frequency": "monthly",
            "start_date": "2026-06-01",
        },
    )
    assert response.status_code == 422


def test_cross_profile_income_is_not_found(api_client: TestClient) -> None:
    owner = _profile(api_client, "Owner")
    other = _profile(api_client, "Other")
    s = _schedule(api_client, owner)
    assert api_client.get(f"/profiles/{other}/income").json() == []
    assert api_client.get(f"/profiles/{other}/income/{s['id']}").status_code == 404
    assert api_client.patch(
        f"/profiles/{other}/income/{s['id']}", json={"amount_cents": 1}
    ).status_code == 404


def test_openapi_exposes_income_routes(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()
    assert "/profiles/{profile_id}/income" in schema["paths"]
    assert "/profiles/{profile_id}/income/occurrences" in schema["paths"]
    assert "/profiles/{profile_id}/income/summary" in schema["paths"]
    assert "/profiles/{profile_id}/income/{schedule_id}" in schema["paths"]
