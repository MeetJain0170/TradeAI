"""Smoke tests for the health endpoint."""

from app.domain.schemas.health import HealthResponse
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_documented_schema() -> None:
    response = client.get("/health")
    payload = response.json()
    assert payload == {"status": "ok"}
    assert HealthResponse.model_validate(payload).status == "ok"


def test_health_v1_returns_envelope() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"

