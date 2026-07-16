"""Tests for the health/liveness endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "spending-tracker-api",
        "version": "0.0.1",
    }


def test_metadata_endpoint() -> None:
    response = client.get("/api")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "spending-tracker-api"
    assert body["status"] == "ok"
    assert body["version"] == "0.0.1"
