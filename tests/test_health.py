import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def test_health_check() -> None:
    async def request_health() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["X-Request-ID"]

    asyncio.run(request_health())
