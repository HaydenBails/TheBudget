"""HTTP contract tests for profile-isolated transaction routes."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory, get_session
from app.main import app
from app.models import Base
from app.schemas.transaction import MAX_SAFE_CENTS, SplitInput


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_db_engine(tmp_path / "transaction-api.db")
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


def _profile(client: TestClient, name: str) -> int:
    response = client.post("/profiles", json={"name": name})
    assert response.status_code == 201
    return int(response.json()["id"])


def _account(client: TestClient, profile_id: int, name: str = "Visa") -> int:
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


def _category_ids(client: TestClient, profile_id: int) -> dict[str, int]:
    response = client.get(f"/profiles/{profile_id}/categories")
    assert response.status_code == 200
    return {item["slug"]: int(item["id"]) for item in response.json()}


def _transaction(
    client: TestClient,
    profile_id: int,
    account_id: int,
    *,
    description: str = "LOBLAWS #1042",
    amount_cents: int = 10_000,
    direction: str = "debit",
    transaction_type: str = "purchase",
    category_id: int | None = None,
    date: str = "2026-07-14",
) -> dict[str, object]:
    response = client.post(
        f"/profiles/{profile_id}/transactions",
        json={
            "account_id": account_id,
            "date": date,
            "raw_description": description,
            "merchant": description.split()[0].title(),
            "amount_cents": amount_cents,
            "direction": direction,
            "type": transaction_type,
            "category_id": category_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_transaction_crud_detail_and_composable_filters(api_client: TestClient) -> None:
    profile_id = _profile(api_client, "Personal")
    account_id = _account(api_client, profile_id)
    categories = _category_ids(api_client, profile_id)
    purchase = _transaction(
        api_client,
        profile_id,
        account_id,
        category_id=categories["groceries"],
    )
    payment = _transaction(
        api_client,
        profile_id,
        account_id,
        description="PAYMENT THANK YOU",
        amount_cents=-25_000,
        direction="credit",
        transaction_type="payment",
        date="2026-07-15",
    )

    transaction_id = int(purchase["id"])
    assert purchase["amount_cents"] == 10_000
    assert purchase["included_in_spending"] is True
    assert purchase["deleted_at"] is None

    detail = api_client.get(
        f"/profiles/{profile_id}/transactions/{transaction_id}"
    ).json()
    assert detail["id"] == transaction_id
    assert detail["splits"] == []
    assert detail["tags"] == []

    patched = api_client.patch(
        f"/profiles/{profile_id}/transactions/{transaction_id}",
        json={"merchant": "Loblaws Market", "notes": "weekly groceries"},
    )
    assert patched.status_code == 200
    assert patched.json()["merchant"] == "Loblaws Market"

    base = f"/profiles/{profile_id}/transactions"
    queries = [
        (f"account_id={account_id}", [int(payment["id"]), transaction_id]),
        (f"category_id={categories['groceries']}", [transaction_id]),
        ("type=purchase", [transaction_id]),
        ("date_from=2026-07-14&date_to=2026-07-14", [transaction_id]),
        ("included_in_spending=true", [transaction_id]),
        ("search=weekly", [transaction_id]),
    ]
    for query, expected_ids in queries:
        response = api_client.get(f"{base}?{query}")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == expected_ids

    reversed_dates = api_client.get(
        f"{base}?date_from=2026-07-16&date_to=2026-07-14"
    )
    assert reversed_dates.status_code == 422


def test_split_and_tag_routes_are_reachable_and_validate_exact_sums(
    api_client: TestClient,
) -> None:
    profile_id = _profile(api_client, "Personal")
    account_id = _account(api_client, profile_id)
    categories = _category_ids(api_client, profile_id)
    transaction = _transaction(api_client, profile_id, account_id)
    transaction_id = int(transaction["id"])
    splits_url = f"/profiles/{profile_id}/transactions/{transaction_id}/splits"
    tags_url = f"/profiles/{profile_id}/transactions/{transaction_id}/tags"

    splits = api_client.put(
        splits_url,
        json={
            "splits": [
                {"category_id": categories["groceries"], "amount_cents": 6_000},
                {"category_id": categories["dining"], "amount_cents": 4_000},
            ]
        },
    )
    assert splits.status_code == 200
    assert sum(item["amount_cents"] for item in splits.json()) == 10_000

    mismatch = api_client.put(
        splits_url,
        json={
            "splits": [
                {"category_id": categories["groceries"], "amount_cents": 6_000},
                {"category_id": categories["dining"], "amount_cents": 3_000},
            ]
        },
    )
    assert mismatch.status_code == 422
    assert "sum" in mismatch.json()["detail"]

    single = api_client.put(
        splits_url,
        json={
            "splits": [
                {"category_id": categories["groceries"], "amount_cents": 10_000}
            ]
        },
    )
    assert single.status_code == 422
    assert "at least two" in single.json()["detail"]

    tags = api_client.put(
        tags_url,
        json={
            "tags": [
                {"name": "Weekly"},
                {"name": "weekly"},
                {"name": "Essentials"},
            ]
        },
    )
    assert tags.status_code == 200
    assert [tag["name"] for tag in tags.json()] == ["Weekly", "Essentials"]

    detail = api_client.get(
        f"/profiles/{profile_id}/transactions/{transaction_id}"
    ).json()
    assert len(detail["splits"]) == 2
    assert {tag["name"] for tag in detail["tags"]} == {"Weekly", "Essentials"}
    assert api_client.put(splits_url, json={"splits": []}).json() == []
    assert api_client.put(tags_url, json={"tags": []}).json() == []


def test_soft_delete_restore_and_cross_profile_not_found_are_uniform(
    api_client: TestClient,
) -> None:
    owner_id = _profile(api_client, "Owner")
    other_id = _profile(api_client, "Other")
    account_id = _account(api_client, owner_id)
    transaction = _transaction(api_client, owner_id, account_id)
    transaction_id = int(transaction["id"])
    owner_base = f"/profiles/{owner_id}/transactions"

    deleted = api_client.delete(f"{owner_base}/{transaction_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"id": transaction_id, "deleted": True}
    assert api_client.get(owner_base).json() == []
    trashed = api_client.get(f"{owner_base}?include_deleted=true").json()
    assert trashed[0]["deleted_at"] is not None

    restored = api_client.post(f"{owner_base}/{transaction_id}/restore")
    assert restored.json() == {"id": transaction_id, "deleted": False}
    assert api_client.get(owner_base).json()[0]["deleted_at"] is None

    expected = {"detail": "transaction not found"}
    responses = [
        api_client.get(f"/profiles/{other_id}/transactions/{transaction_id}"),
        api_client.patch(
            f"/profiles/{other_id}/transactions/{transaction_id}",
            json={"merchant": "Leak"},
        ),
        api_client.delete(f"/profiles/{other_id}/transactions/{transaction_id}"),
        api_client.post(
            f"/profiles/{other_id}/transactions/{transaction_id}/restore"
        ),
        api_client.put(
            f"/profiles/{other_id}/transactions/{transaction_id}/splits",
            json={"splits": []},
        ),
        api_client.put(
            f"/profiles/{other_id}/transactions/{transaction_id}/tags",
            json={"tags": []},
        ),
    ]
    assert all(response.status_code == 404 for response in responses)
    assert all(response.json() == expected for response in responses)


def test_bulk_categorize_and_inclusion_return_exact_counts(api_client: TestClient) -> None:
    profile_id = _profile(api_client, "Personal")
    account_id = _account(api_client, profile_id)
    categories = _category_ids(api_client, profile_id)
    first = _transaction(api_client, profile_id, account_id, description="ONE SHOP")
    second = _transaction(api_client, profile_id, account_id, description="TWO SHOP")
    ids = [int(first["id"]), int(second["id"])]
    bulk_url = f"/profiles/{profile_id}/transactions/bulk"

    categorized = api_client.patch(
        bulk_url,
        json={
            "action": "categorize",
            "transaction_ids": ids,
            "category_id": categories["shopping"],
        },
    )
    assert categorized.status_code == 200
    assert categorized.json()["updated_count"] == 2
    assert {item["category_id"] for item in categorized.json()["transactions"]} == {
        categories["shopping"]
    }
    assert all(
        item["categorization_status"] == "manual"
        for item in categorized.json()["transactions"]
    )

    uncategorized = api_client.patch(
        bulk_url,
        json={
            "action": "categorize",
            "transaction_ids": ids,
            "category_id": None,
        },
    )
    assert uncategorized.status_code == 200
    assert all(item["category_id"] is None for item in uncategorized.json()["transactions"])
    assert all(
        item["categorization_status"] == "uncategorized"
        for item in uncategorized.json()["transactions"]
    )

    excluded = api_client.patch(
        bulk_url,
        json={
            "action": "set_spending_inclusion",
            "transaction_ids": ids,
            "included_in_spending": False,
            "exclusion_reason": "Personal review",
        },
    )
    assert excluded.status_code == 200
    assert excluded.json()["updated_count"] == 2
    assert all(not item["included_in_spending"] for item in excluded.json()["transactions"])
    assert all(
        item["exclusion_reason"] == "Personal review"
        for item in excluded.json()["transactions"]
    )

    included = api_client.patch(
        bulk_url,
        json={
            "action": "set_spending_inclusion",
            "transaction_ids": ids,
            "included_in_spending": True,
        },
    )
    assert included.status_code == 200
    assert all(item["included_in_spending"] for item in included.json()["transactions"])
    assert all(item["exclusion_reason"] is None for item in included.json()["transactions"])


@pytest.mark.parametrize(
    "transaction_ids",
    [[], [1, 1], list(range(1, 502))],
)
def test_bulk_rejects_empty_duplicate_and_over_limit_ids(
    api_client: TestClient,
    transaction_ids: list[int],
) -> None:
    profile_id = _profile(api_client, f"Bulk {len(transaction_ids)}")
    response = api_client.patch(
        f"/profiles/{profile_id}/transactions/bulk",
        json={
            "action": "categorize",
            "transaction_ids": transaction_ids,
            "category_id": None,
        },
    )
    assert response.status_code == 422


def test_bulk_cross_profile_failure_rolls_back_all_mutations(api_client: TestClient) -> None:
    owner_id = _profile(api_client, "Owner")
    other_id = _profile(api_client, "Other")
    owner_account = _account(api_client, owner_id)
    other_account = _account(api_client, other_id)
    owner_categories = _category_ids(api_client, owner_id)
    owned = _transaction(api_client, owner_id, owner_account)
    foreign = _transaction(api_client, other_id, other_account)
    owned_id = int(owned["id"])

    response = api_client.patch(
        f"/profiles/{owner_id}/transactions/bulk",
        json={
            "action": "categorize",
            "transaction_ids": [owned_id, int(foreign["id"])],
            "category_id": owner_categories["shopping"],
        },
    )
    assert response.status_code == 404
    unchanged = api_client.get(
        f"/profiles/{owner_id}/transactions/{owned_id}"
    ).json()
    assert unchanged["category_id"] is None


def test_bulk_domain_failure_is_atomic(api_client: TestClient) -> None:
    profile_id = _profile(api_client, "Personal")
    account_id = _account(api_client, profile_id)
    purchase = _transaction(api_client, profile_id, account_id)
    payment = _transaction(
        api_client,
        profile_id,
        account_id,
        description="PAYMENT",
        amount_cents=-5_000,
        direction="credit",
        transaction_type="payment",
    )
    bulk_url = f"/profiles/{profile_id}/transactions/bulk"
    purchase_id = int(purchase["id"])

    excluded = api_client.patch(
        bulk_url,
        json={
            "action": "set_spending_inclusion",
            "transaction_ids": [purchase_id],
            "included_in_spending": False,
            "exclusion_reason": "Review",
        },
    )
    assert excluded.status_code == 200

    failed = api_client.patch(
        bulk_url,
        json={
            "action": "set_spending_inclusion",
            "transaction_ids": [purchase_id, int(payment["id"])],
            "included_in_spending": True,
        },
    )
    assert failed.status_code == 422
    unchanged = api_client.get(
        f"/profiles/{profile_id}/transactions/{purchase_id}"
    ).json()
    assert unchanged["included_in_spending"] is False
    assert unchanged["exclusion_reason"] == "Review"


def test_transaction_validation_and_openapi_contract(api_client: TestClient) -> None:
    profile_id = _profile(api_client, "Personal")
    account_id = _account(api_client, profile_id)
    invalid = api_client.post(
        f"/profiles/{profile_id}/transactions",
        json={
            "account_id": account_id,
            "date": "2026-07-14",
            "raw_description": "Bad cents",
            "amount_cents": 12.5,
            "direction": "debit",
            "type": "purchase",
        },
    )
    assert invalid.status_code == 422

    paths = api_client.get("/openapi.json").json()["paths"]
    expected = {
        "/profiles/{profile_id}/transactions",
        "/profiles/{profile_id}/transactions/bulk",
        "/profiles/{profile_id}/transactions/{transaction_id}",
        "/profiles/{profile_id}/transactions/{transaction_id}/restore",
        "/profiles/{profile_id}/transactions/{transaction_id}/splits",
        "/profiles/{profile_id}/transactions/{transaction_id}/tags",
    }
    assert expected <= set(paths)
    assert "patch" in paths["/profiles/{profile_id}/transactions/bulk"]
    assert "put" in paths[
        "/profiles/{profile_id}/transactions/{transaction_id}/splits"
    ]


@pytest.mark.parametrize(
    ("invalid_amount", "direction"),
    [
        (MAX_SAFE_CENTS + 1, "debit"),
        (-MAX_SAFE_CENTS - 1, "credit"),
    ],
)
def test_api_rejects_unsafe_create_update_and_split_cent_amounts(
    api_client: TestClient,
    invalid_amount: int,
    direction: str,
) -> None:
    profile_id = _profile(api_client, "Safe cents")
    account_id = _account(api_client, profile_id)
    categories = _category_ids(api_client, profile_id)
    base_url = f"/profiles/{profile_id}/transactions"
    invalid_create = api_client.post(
        base_url,
        json={
            "account_id": account_id,
            "date": "2026-07-16",
            "raw_description": "Outside safe integer range",
            "amount_cents": invalid_amount,
            "direction": direction,
            "type": "purchase" if direction == "debit" else "refund",
        },
    )
    assert invalid_create.status_code == 422
    assert "amount_cents" in invalid_create.text

    transaction = _transaction(api_client, profile_id, account_id)
    transaction_url = f"{base_url}/{transaction['id']}"
    invalid_update = api_client.patch(
        transaction_url,
        json={"amount_cents": invalid_amount, "direction": direction},
    )
    assert invalid_update.status_code == 422
    assert "amount_cents" in invalid_update.text

    invalid_splits = api_client.put(
        f"{transaction_url}/splits",
        json={
            "splits": [
                {
                    "category_id": categories["groceries"],
                    "amount_cents": invalid_amount,
                },
                {"category_id": categories["dining"], "amount_cents": 1},
            ]
        },
    )
    assert invalid_splits.status_code == 422
    assert "amount_cents" in invalid_splits.text


def test_safe_cent_boundaries_round_trip_exactly(api_client: TestClient) -> None:
    profile_id = _profile(api_client, "Boundary cents")
    account_id = _account(api_client, profile_id)
    categories = _category_ids(api_client, profile_id)

    positive = _transaction(
        api_client,
        profile_id,
        account_id,
        description="Maximum safe debit",
        amount_cents=MAX_SAFE_CENTS,
    )
    assert positive["amount_cents"] == MAX_SAFE_CENTS

    negative = _transaction(
        api_client,
        profile_id,
        account_id,
        description="Maximum safe credit",
        amount_cents=-MAX_SAFE_CENTS,
        direction="credit",
        transaction_type="refund",
    )
    assert negative["amount_cents"] == -MAX_SAFE_CENTS

    transaction_url = f"/profiles/{profile_id}/transactions/{negative['id']}"
    for amount_cents, direction in (
        (MAX_SAFE_CENTS, "debit"),
        (-MAX_SAFE_CENTS, "credit"),
    ):
        response = api_client.patch(
            transaction_url,
            json={
                "amount_cents": amount_cents,
                "direction": direction,
                "type": "purchase" if direction == "debit" else "refund",
            },
        )
        assert response.status_code == 200
        assert response.json()["amount_cents"] == amount_cents

    splits = api_client.put(
        f"/profiles/{profile_id}/transactions/{positive['id']}/splits",
        json={
            "splits": [
                {
                    "category_id": categories["groceries"],
                    "amount_cents": MAX_SAFE_CENTS - 1,
                },
                {"category_id": categories["dining"], "amount_cents": 1},
            ]
        },
    )
    assert splits.status_code == 200
    assert sum(item["amount_cents"] for item in splits.json()) == MAX_SAFE_CENTS
    assert SplitInput(category_id=1, amount_cents=MAX_SAFE_CENTS).amount_cents == MAX_SAFE_CENTS
    assert SplitInput(category_id=1, amount_cents=-MAX_SAFE_CENTS).amount_cents == -MAX_SAFE_CENTS

    schemas = api_client.get("/openapi.json").json()["components"]["schemas"]
    for schema_name in ("SplitInput", "SplitRead", "TransactionCreate", "TransactionRead"):
        amount_schema = schemas[schema_name]["properties"]["amount_cents"]
        assert amount_schema["minimum"] == -MAX_SAFE_CENTS
        assert amount_schema["maximum"] == MAX_SAFE_CENTS
