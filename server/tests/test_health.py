from animedownloader_api.app import create_app
from fastapi.testclient import TestClient


def test_health() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
