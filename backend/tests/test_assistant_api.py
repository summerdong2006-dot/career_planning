from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.auth.service import get_current_user


@pytest.mark.asyncio
async def test_assistant_chat_returns_reply(monkeypatch):
    async def override_user():
        return SimpleNamespace(id=1, email="demo@example.com", display_name="Demo User")

    async def mock_generate_reply(request):
        assert request.messages[-1].content == "这个页面下一步做什么？"
        assert request.context is not None
        assert request.context.page_name == "dashboard"
        return "你可以先生成学生画像，再查看岗位推荐。", "zai_sdk", "glm-4.7-flash"

    monkeypatch.setattr("app.api.routes.assistant.generate_assistant_reply", mock_generate_reply)
    app.dependency_overrides[get_current_user] = override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/assistant/chat",
            json={
                "messages": [{"role": "user", "content": "这个页面下一步做什么？"}],
                "context": {"page_name": "dashboard", "page_label": "工作台"},
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "reply": "你可以先生成学生画像，再查看岗位推荐。",
        "provider": "zai_sdk",
        "model": "glm-4.7-flash",
        "used_context": True,
    }
