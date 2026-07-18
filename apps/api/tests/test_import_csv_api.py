"""HTTP contract test: importing a TD account-activity .csv via the preview API."""

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
FIXTURE = REPOSITORY_ROOT / "fixtures" / "statements" / "td" / "td_account_activity.csv"
CSV_MIME = "text/csv"


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
        json={"issuer": "TD", "display_name": "TD Chequing", "color": "#12805c", "kind": "asset"},
    ).json()["id"]
    return pid, aid


def _preview(client: TestClient, pid: int, aid: int, filename: str = "activity.csv"):
    with FIXTURE.open("rb") as stream:
        return client.post(
            f"/profiles/{pid}/imports/preview",
            files={"statement": (filename, stream, CSV_MIME)},
            data={"account_id": str(aid)},
        )


def test_csv_preview_uses_td_csv_parser_and_reconciles(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    response = _preview(api_client, pid, aid)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parser_name"] == "td_csv"
    assert body["issuer"] == "TD"
    assert body["transaction_count"] == 10
    assert body["reconciliation_delta_cents"] == 0
    assert body["validation_status"] == "validated"


def test_csv_preview_commits_into_the_ledger(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    import_id = _preview(api_client, pid, aid).json()["id"]
    committed = api_client.post(f"/profiles/{pid}/imports/{import_id}/commit", json={})
    assert committed.status_code == 200, committed.text
    txns = api_client.get(f"/profiles/{pid}/transactions").json()
    assert len(txns) == 10
    # Purchases are included in spending; transfers/fees/payments/income are not.
    purchases = [t for t in txns if t["type"] == "purchase"]
    assert purchases and all(t["included_in_spending"] for t in purchases)
    income = [t for t in txns if t["type"] == "income"]
    assert len(income) == 1 and income[0]["amount_cents"] == -200000


def test_reimporting_same_csv_is_blocked_as_duplicate(api_client: TestClient) -> None:
    pid, aid = _profile_and_account(api_client)
    assert _preview(api_client, pid, aid).status_code == 201
    assert _preview(api_client, pid, aid).status_code == 409
