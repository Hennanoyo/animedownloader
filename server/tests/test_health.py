import httpx
import pytest

from animedownloader_api.app import create_app


@pytest.mark.anyio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
