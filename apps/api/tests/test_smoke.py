from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_returns_service_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "JJ AI Platform API"
    assert payload["version"]
    assert payload["environment"]


def test_health_endpoint_is_available() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "jj-ai-platform-api",
    }


def test_openapi_schema_is_generated() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "JJ AI Platform API"
    assert "/health" in payload["paths"]
