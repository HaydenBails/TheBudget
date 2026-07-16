"""HTTP contract tests for profile and isolated account routes."""

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


def _create_profile(client: TestClient, name: str) -> dict[str, object]:
    response = client.post("/profiles", json={"name": name})
    assert response.status_code == 201
    return response.json()


def _create_account(
    client: TestClient,
    profile_id: int,
    name: str,
    *,
    last4: str = "1234",
) -> dict[str, object]:
    response = client.post(
        f"/profiles/{profile_id}/accounts",
        json={
            "issuer": "TD",
            "display_name": name,
            "color": "#4f6bff",
            "last4": last4,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_profile_crud_archive_restore_and_default_filter(api_client: TestClient) -> None:
    profile = _create_profile(api_client, "  Personal  ")
    profile_id = int(profile["id"])

    assert profile["name"] == "Personal"
    assert profile["base_currency"] == "CAD"
    assert profile["is_archived"] is False
    assert api_client.get(f"/profiles/{profile_id}").json() == profile

    renamed = api_client.patch(
        f"/profiles/{profile_id}",
        json={"name": "Household"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Household"

    archived = api_client.post(f"/profiles/{profile_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert api_client.get("/profiles").json() == []
    assert api_client.get("/profiles?include_archived=true").json()[0]["id"] == profile_id

    restored = api_client.post(f"/profiles/{profile_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["is_archived"] is False


def test_profile_validation_and_missing_responses(api_client: TestClient) -> None:
    assert api_client.post("/profiles", json={"name": "   "}).status_code == 422
    profile = _create_profile(api_client, "Personal")
    profile_id = int(profile["id"])

    invalid_null = api_client.patch(
        f"/profiles/{profile_id}",
        json={"name": None},
    )
    missing = api_client.get("/profiles/99999")

    assert invalid_null.status_code == 422
    assert "name" in invalid_null.json()["detail"]
    assert missing.status_code == 404
    assert missing.json() == {"detail": "profile not found"}


def test_account_crud_is_scoped_to_path_profile(api_client: TestClient) -> None:
    owner = _create_profile(api_client, "Owner")
    other = _create_profile(api_client, "Other")
    owner_id = int(owner["id"])
    other_id = int(other["id"])
    account = _create_account(api_client, owner_id, "Cash Back")
    account_id = int(account["id"])

    assert account["profile_id"] == owner_id
    assert api_client.get(f"/profiles/{owner_id}/accounts/{account_id}").json() == account
    assert [item["id"] for item in api_client.get(
        f"/profiles/{owner_id}/accounts"
    ).json()] == [account_id]
    assert api_client.get(f"/profiles/{other_id}/accounts").json() == []

    updated = api_client.patch(
        f"/profiles/{owner_id}/accounts/{account_id}",
        json={"display_name": "Everyday", "last4": None},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Everyday"
    assert updated.json()["last4"] is None


def test_cross_profile_account_operations_match_missing_response(
    api_client: TestClient,
) -> None:
    owner = _create_profile(api_client, "Owner")
    other = _create_profile(api_client, "Other")
    owner_id = int(owner["id"])
    other_id = int(other["id"])
    account = _create_account(api_client, owner_id, "Private")
    account_id = int(account["id"])
    expected = {"detail": "account not found"}

    responses = [
        api_client.get(f"/profiles/{other_id}/accounts/{account_id}"),
        api_client.get(f"/profiles/{other_id}/accounts/99999"),
        api_client.patch(
            f"/profiles/{other_id}/accounts/{account_id}",
            json={"display_name": "Leaked"},
        ),
        api_client.post(f"/profiles/{other_id}/accounts/{account_id}/archive"),
        api_client.post(f"/profiles/{other_id}/accounts/{account_id}/restore"),
    ]

    assert all(response.status_code == 404 for response in responses)
    assert all(response.json() == expected for response in responses)
    unchanged = api_client.get(f"/profiles/{owner_id}/accounts/{account_id}").json()
    assert unchanged["display_name"] == "Private"
    assert unchanged["is_archived"] is False


def test_account_archive_restore_and_validation(api_client: TestClient) -> None:
    profile = _create_profile(api_client, "Personal")
    profile_id = int(profile["id"])
    account = _create_account(api_client, profile_id, "Card")
    account_id = int(account["id"])

    invalid = api_client.post(
        f"/profiles/{profile_id}/accounts",
        json={"issuer": "VISA", "display_name": "Bad", "color": "blue"},
    )
    invalid_null = api_client.patch(
        f"/profiles/{profile_id}/accounts/{account_id}",
        json={"display_name": None},
    )
    assert invalid.status_code == 422
    assert invalid_null.status_code == 422
    assert "display_name" in invalid_null.json()["detail"]

    archived = api_client.post(
        f"/profiles/{profile_id}/accounts/{account_id}/archive"
    )
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert api_client.get(f"/profiles/{profile_id}/accounts").json() == []
    included = api_client.get(
        f"/profiles/{profile_id}/accounts?include_archived=true"
    )
    assert included.json()[0]["id"] == account_id

    restored = api_client.post(
        f"/profiles/{profile_id}/accounts/{account_id}/restore"
    )
    assert restored.status_code == 200
    assert restored.json()["is_archived"] is False


def test_missing_profile_rejects_account_collection_operations(
    api_client: TestClient,
) -> None:
    listed = api_client.get("/profiles/99999/accounts")
    created = api_client.post(
        "/profiles/99999/accounts",
        json={
            "issuer": "TD",
            "display_name": "Orphan",
            "color": "#4f6bff",
        },
    )

    assert listed.status_code == 404
    assert created.status_code == 404
    assert listed.json() == created.json() == {"detail": "profile not found"}


def test_openapi_contains_typed_routes_and_no_hard_delete(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()
    paths = schema["paths"]

    assert {"get", "post"} <= paths["/profiles"].keys()
    assert {"get", "patch"} <= paths["/profiles/{profile_id}"].keys()
    assert "post" in paths["/profiles/{profile_id}/archive"]
    assert "post" in paths["/profiles/{profile_id}/restore"]
    assert {"get", "post"} <= paths["/profiles/{profile_id}/accounts"].keys()
    assert {"get", "patch"} <= paths[
        "/profiles/{profile_id}/accounts/{account_id}"
    ].keys()
    profile_account_paths = {
        path: operations
        for path, operations in paths.items()
        if path.startswith("/profiles") and "/transactions" not in path
    }
    assert all("delete" not in operations for operations in profile_account_paths.values())
    assert schema["components"]["schemas"]["AccountRead"]["properties"][
        "profile_id"
    ]["type"] == "integer"
