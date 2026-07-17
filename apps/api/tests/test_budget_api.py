"""HTTP contract tests for profile-isolated monthly budget routes."""

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


def _create_profile(client: TestClient, name: str) -> int:
    response = client.post("/profiles", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _first_category_id(client: TestClient, profile_id: int) -> int:
    response = client.get(f"/profiles/{profile_id}/categories")
    assert response.status_code == 200
    return response.json()[0]["id"]


def test_create_overall_and_category_budgets(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    cid = _first_category_id(api_client, pid)

    overall = api_client.post(
        f"/profiles/{pid}/budgets",
        json={"period_month": "2026-07", "limit_cents": 400000},
    )
    assert overall.status_code == 201
    assert overall.json()["category_id"] is None
    assert overall.json()["limit_cents"] == 400000

    category = api_client.post(
        f"/profiles/{pid}/budgets",
        json={"category_id": cid, "period_month": "2026-07", "limit_cents": 50000},
    )
    assert category.status_code == 201
    assert category.json()["category_id"] == cid


def test_duplicate_overall_budget_conflicts(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    body = {"period_month": "2026-07", "limit_cents": 400000}
    assert api_client.post(f"/profiles/{pid}/budgets", json=body).status_code == 201
    dup = api_client.post(f"/profiles/{pid}/budgets", json=body)
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"]


def test_duplicate_category_budget_conflicts(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    cid = _first_category_id(api_client, pid)
    body = {"category_id": cid, "period_month": "2026-07", "limit_cents": 50000}
    assert api_client.post(f"/profiles/{pid}/budgets", json=body).status_code == 201
    assert api_client.post(f"/profiles/{pid}/budgets", json=body).status_code == 409


def test_same_category_different_months_allowed(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    cid = _first_category_id(api_client, pid)
    july = api_client.post(
        f"/profiles/{pid}/budgets",
        json={"category_id": cid, "period_month": "2026-07", "limit_cents": 50000},
    )
    august = api_client.post(
        f"/profiles/{pid}/budgets",
        json={"category_id": cid, "period_month": "2026-08", "limit_cents": 60000},
    )
    assert july.status_code == 201
    assert august.status_code == 201


def test_list_filters_by_month(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    api_client.post(
        f"/profiles/{pid}/budgets",
        json={"period_month": "2026-07", "limit_cents": 400000},
    )
    api_client.post(
        f"/profiles/{pid}/budgets",
        json={"period_month": "2026-08", "limit_cents": 410000},
    )
    july = api_client.get(f"/profiles/{pid}/budgets", params={"period_month": "2026-07"})
    assert july.status_code == 200
    assert [b["period_month"] for b in july.json()] == ["2026-07"]
    every = api_client.get(f"/profiles/{pid}/budgets")
    assert len(every.json()) == 2


def test_category_must_belong_to_profile(api_client: TestClient) -> None:
    owner = _create_profile(api_client, "Owner")
    other = _create_profile(api_client, "Other")
    foreign_category = _first_category_id(api_client, other)
    response = api_client.post(
        f"/profiles/{owner}/budgets",
        json={
            "category_id": foreign_category,
            "period_month": "2026-07",
            "limit_cents": 50000,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "category not found"


def test_cross_profile_budget_is_not_found(api_client: TestClient) -> None:
    owner = _create_profile(api_client, "Owner")
    other = _create_profile(api_client, "Other")
    created = api_client.post(
        f"/profiles/{owner}/budgets",
        json={"period_month": "2026-07", "limit_cents": 400000},
    )
    budget_id = created.json()["id"]
    # The other profile cannot see or fetch the owner's budget.
    assert api_client.get(f"/profiles/{other}/budgets").json() == []
    fetched = api_client.get(f"/profiles/{other}/budgets/{budget_id}")
    assert fetched.status_code == 404


def test_update_and_delete_budget(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    created = api_client.post(
        f"/profiles/{pid}/budgets",
        json={"period_month": "2026-07", "limit_cents": 400000},
    )
    budget_id = created.json()["id"]

    updated = api_client.patch(
        f"/profiles/{pid}/budgets/{budget_id}",
        json={"limit_cents": 450000},
    )
    assert updated.status_code == 200
    assert updated.json()["limit_cents"] == 450000

    deleted = api_client.delete(f"/profiles/{pid}/budgets/{budget_id}")
    assert deleted.status_code == 204
    assert api_client.get(f"/profiles/{pid}/budgets/{budget_id}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"period_month": "2026-13", "limit_cents": 1000},  # invalid month
        {"period_month": "2026-7", "limit_cents": 1000},  # unpadded month
        {"period_month": "2026-07", "limit_cents": 0},  # non-positive limit
        {"period_month": "2026-07", "limit_cents": -5},  # negative limit
    ],
)
def test_invalid_budget_payloads_rejected(
    api_client: TestClient, payload: dict[str, object]
) -> None:
    pid = _create_profile(api_client, "Personal")
    response = api_client.post(f"/profiles/{pid}/budgets", json=payload)
    assert response.status_code == 422


def test_openapi_exposes_budget_routes(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()
    assert "/profiles/{profile_id}/budgets" in schema["paths"]
    assert "/profiles/{profile_id}/budgets/{budget_id}" in schema["paths"]
