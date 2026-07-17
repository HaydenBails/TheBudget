"""Tests for merchant auto-categorization rules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory, get_session
from app.main import app
from app.models import Base
from app.services.merchant_rules import normalize_merchant_key, normalize_search_text


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


def _profile(client: TestClient) -> tuple[int, int]:
    pid = client.post("/profiles", json={"name": "Hayden"}).json()["id"]
    aid = client.post(
        f"/profiles/{pid}/accounts",
        json={"issuer": "AMEX", "display_name": "Amex", "color": "#7c5cff"},
    ).json()["id"]
    return pid, aid


def _purchase(client: TestClient, pid: int, aid: int, merchant: str, cents: int = 1000) -> int:
    body = {
        "account_id": aid,
        "date": "2026-06-15",
        "raw_description": merchant,
        "merchant": merchant,
        "amount_cents": cents,
        "direction": "debit",
        "type": "purchase",
    }
    return client.post(f"/profiles/{pid}/transactions", json=body).json()["id"]


def _category_id(client: TestClient, pid: int, slug_name: str) -> int:
    cats = client.get(f"/profiles/{pid}/categories").json()
    return next(c["id"] for c in cats if c["name"] == slug_name)


def test_normalizers() -> None:
    assert normalize_merchant_key("STARBUCKS COFFEE #2327", "") == "STARBUCKS COFFEE"
    assert normalize_search_text("UBER CANADA/UBEREATS", "") == "UBER CANADA UBEREATS"


def test_new_profile_is_seeded_with_generic_rules(api_client: TestClient) -> None:
    pid, _ = _profile(api_client)
    rules = api_client.get(f"/profiles/{pid}/merchant-rules").json()
    assert len(rules) > 30
    assert all(r["is_default"] for r in rules)
    patterns = {r["pattern"] for r in rules}
    assert "SPOTIFY" in patterns and "UBEREATS" in patterns


def test_apply_rules_auto_categorizes_common_merchants(api_client: TestClient) -> None:
    pid, aid = _profile(api_client)
    _purchase(api_client, pid, aid, "SPOTIFY")
    _purchase(api_client, pid, aid, "UBER CANADA/UBEREATS")
    _purchase(api_client, pid, aid, "PETRO-CANADA 29514")
    _purchase(api_client, pid, aid, "SOME UNKNOWN LOCAL SHOP")

    result = api_client.post(f"/profiles/{pid}/merchant-rules/apply")
    assert result.status_code == 200
    assert result.json()["categorized"] == 3  # the unknown shop stays uncategorized

    txns = {t["merchant"]: t for t in api_client.get(f"/profiles/{pid}/transactions").json()}
    entertainment = _category_id(api_client, pid, "Entertainment")
    dining = _category_id(api_client, pid, "Dining & Takeaway")
    assert txns["SPOTIFY"]["category_id"] == entertainment
    assert txns["SPOTIFY"]["categorization_status"] == "rule_applied"
    # "UBEREATS" (dining) beats the shorter "UBER CANADA" (transport) rule.
    assert txns["UBER CANADA/UBEREATS"]["category_id"] == dining
    assert txns["SOME UNKNOWN LOCAL SHOP"]["category_id"] is None


def test_learn_from_history_builds_exact_rules(api_client: TestClient) -> None:
    pid, aid = _profile(api_client)
    tid = _purchase(api_client, pid, aid, "MY CORNER STORE")
    groceries = _category_id(api_client, pid, "Groceries")
    api_client.patch(f"/profiles/{pid}/transactions/{tid}", json={"category_id": groceries})

    learn = api_client.post(f"/profiles/{pid}/merchant-rules/learn")
    assert learn.status_code == 200
    assert learn.json()["created"] >= 1

    # A later charge from the same merchant now auto-categorizes.
    _purchase(api_client, pid, aid, "MY CORNER STORE")
    api_client.post(f"/profiles/{pid}/merchant-rules/apply")
    all_txns = api_client.get(f"/profiles/{pid}/transactions").json()
    matched = [t for t in all_txns if t["category_id"] == groceries]
    assert len(matched) == 2


def test_manual_rule_crud_and_cross_profile_isolation(api_client: TestClient) -> None:
    owner, _ = _profile(api_client)
    other, _ = _profile(api_client)
    groceries = _category_id(api_client, owner, "Groceries")
    created = api_client.post(
        f"/profiles/{owner}/merchant-rules",
        json={"pattern": "farmers market", "category_id": groceries, "match_type": "contains"},
    )
    assert created.status_code == 201
    assert created.json()["pattern"] == "FARMERS MARKET"
    rule_id = created.json()["id"]
    assert api_client.get(f"/profiles/{other}/merchant-rules/{rule_id}").status_code == 404
    assert api_client.delete(f"/profiles/{owner}/merchant-rules/{rule_id}").status_code == 204


def test_openapi_exposes_merchant_rule_routes(api_client: TestClient) -> None:
    paths = api_client.get("/openapi.json").json()["paths"]
    assert "/profiles/{profile_id}/merchant-rules" in paths
    assert "/profiles/{profile_id}/merchant-rules/apply" in paths
    assert "/profiles/{profile_id}/merchant-rules/learn" in paths
