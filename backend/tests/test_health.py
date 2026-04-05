from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_check_returns_ok(monkeypatch):
    async def mock_db_check() -> bool:
        return True

    monkeypatch.setattr("app.api.routes.health.check_database_connection", mock_db_check)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
