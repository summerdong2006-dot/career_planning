from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.main import app


async def test_job_profile_extract_api_accepts_inline_job_data():
    async def override_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)
    payload = {
        "job_data": {
            "position_name": "数据分析师",
            "job_category": "数据分析",
            "company_full_name": "深圳数图科技股份有限公司",
            "industry": "企业服务/数据服务",
            "job_description": "负责业务指标分析和BI报表建设，熟悉SQL，本科及以上学历。",
            "job_tags": ["SQL"]
        },
        "persist": False
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/job-profiles/extract", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    evidence = body["profile"]["extracted_evidence"]
    assert body["profile"]["job_title"] == "数据分析师"
    assert body["profile"]["education_requirement"] == "本科"
    assert "SQL" in body["profile"]["must_have_skills"]
    assert isinstance(body["profile"]["summary"], str)
    assert isinstance(evidence, dict)
    assert all(isinstance(value, list) for value in evidence.values())
    assert body["persisted"] is False
