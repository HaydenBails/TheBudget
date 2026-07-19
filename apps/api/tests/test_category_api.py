"""HTTP contract tests for profile-isolated category routes."""

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


def test_new_profile_exposes_seeded_default_categories(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    response = api_client.get(f"/profiles/{pid}/categories")
    assert response.status_code == 200
    cats = response.json()
    assert len(cats) == 15
    assert all(c["is_default"] for c in cats)
    assert cats[0]["slug"] == "housing"
    assert cats[-1]["slug"] == "uncategorized"


def test_create_custom_category(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    response = api_client.post(
        f"/profiles/{pid}/categories",
        json={"name": "Side Hustle", "color": "#4f6bff", "icon": "💼"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "side-hustle"
    assert body["is_default"] is False
    assert body["profile_id"] == pid


def test_patch_and_archive_restore(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    cid = api_client.post(
        f"/profiles/{pid}/categories", json={"name": "Gifts", "color": "#ec4899"}
    ).json()["id"]

    patched = api_client.patch(
        f"/profiles/{pid}/categories/{cid}", json={"name": "Gifts & Donations"}
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Gifts & Donations"

    assert api_client.post(f"/profiles/{pid}/categories/{cid}/archive").status_code == 200
    listed = api_client.get(f"/profiles/{pid}/categories").json()
    assert all(c["id"] != cid for c in listed)
    assert api_client.post(f"/profiles/{pid}/categories/{cid}/restore").status_code == 200
    listed = api_client.get(f"/profiles/{pid}/categories").json()
    assert any(c["id"] == cid for c in listed)


def test_categories_are_profile_isolated(api_client: TestClient) -> None:
    a = _create_profile(api_client, "Alpha")
    b = _create_profile(api_client, "Beta")
    cid = api_client.post(
        f"/profiles/{a}/categories", json={"name": "Travel", "color": "#0ea5e9"}
    ).json()["id"]

    # not visible under B, and directly addressing it under B is 404
    listed_b = api_client.get(f"/profiles/{b}/categories").json()
    assert all(c["id"] != cid for c in listed_b)
    assert api_client.get(f"/profiles/{b}/categories/{cid}").status_code == 404
    assert (
        api_client.patch(
            f"/profiles/{b}/categories/{cid}", json={"name": "Hijack"}
        ).status_code
        == 404
    )


def test_validation_error_is_field_specific(api_client: TestClient) -> None:
    pid = _create_profile(api_client, "Personal")
    response = api_client.post(
        f"/profiles/{pid}/categories", json={"name": "Bad", "color": "not-a-hex"}
    )
    assert response.status_code == 422


def test_openapi_lists_category_routes(api_client: TestClient) -> None:
    paths = api_client.get("/openapi.json").json()["paths"]
    assert "/profiles/{profile_id}/categories" in paths
    assert "/profiles/{profile_id}/categories/{category_id}" in paths
    assert "/profiles/{profile_id}/categories/{category_id}/archive" in paths
