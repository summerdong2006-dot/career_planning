from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.modules.student_profile.models import StudentProfileRecord


async def _seed_student_profile(session) -> StudentProfileRecord:
    payload = {
        "student_name": "张同学",
        "school": "华南理工大学",
        "major": "计算机科学与技术",
        "education": "本科",
        "grade": "大四",
        "summary": "计算机科学与技术专业学生，熟悉 Python、FastAPI、React、MySQL、Redis、Git，完成职业规划系统和校园二手交易平台项目，有后端开发实习 3 个月，目标岗位为后端开发工程师，目标城市深圳。",
        "skills": ["Python", "FastAPI", "React", "MySQL", "Redis", "Git"],
        "projects": [
            {
                "name": "基于 React + FastAPI 的职业规划系统",
                "role": "全栈开发",
                "description": "负责前端页面、接口联调和核心业务流程实现。",
            },
            {
                "name": "校园二手交易平台",
                "role": "后端开发",
                "description": "负责商品发布、订单流转和数据库设计。",
            },
        ],
        "internships": [
            {
                "company": "深圳某互联网公司",
                "role": "后端开发实习生",
                "description": "后端开发实习 3 个月，参与接口开发、联调和 MySQL/Redis 相关工作。",
            }
        ],
        "career_intention": "后端开发工程师，目标城市深圳",
        "certificates": ["CET-6"],
        "innovation_experiences": ["参与校内创新项目并完成原型开发"],
        "ability_scores": {
            "professional_skills": 88,
            "innovation": 75,
            "learning": 84,
            "stress_tolerance": 72,
            "communication": 78,
            "internship_ability": 80,
        },
        "completeness_score": 92,
        "competitiveness_score": 86,
        "missing_items": [],
        "evidence": {"summary": ["技术方向明确"]},
    }
    record = StudentProfileRecord(
        student_id="demo_cs_001",
        profile_version=1,
        summary=payload["summary"],
        school=payload["school"],
        major=payload["major"],
        education=payload["education"],
        grade=payload["grade"],
        career_intention=payload["career_intention"],
        resume_source="resume",
        completeness_score=payload["completeness_score"],
        competitiveness_score=payload["competitiveness_score"],
        ability_scores=payload["ability_scores"],
        profile_json=payload,
        extracted_evidence=payload["evidence"],
        missing_items=payload["missing_items"],
        raw_profile_payload=payload,
    )
    session.add(record)
    await session.flush()
    return record


@pytest_asyncio.fixture
async def resume_api_session(tmp_path: Path):
    db_path = tmp_path / "resume_api.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        student = await _seed_student_profile(session)
        await session.commit()
        yield session, student.id
    await engine.dispose()


async def _build_client(session):
    async def override_db():
        yield session

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_resume_generate_get_update_and_export_api(resume_api_session):
    session, student_profile_id = resume_api_session
    async with await _build_client(session) as client:
        generate_response = await client.post(
            "/api/v1/resumes/generate",
            json={
                "student_profile_id": student_profile_id,
                "target_job": "前端开发",
                "style": "campus",
                "persist": True,
            },
        )
        assert generate_response.status_code == 200
        generated = generate_response.json()
        resume_id = generated["resume_id"]

        get_response = await client.get(f"/api/v1/resumes/{resume_id}")
        update_response = await client.put(
            f"/api/v1/resumes/{resume_id}",
            json={
                "summary": "面向前端开发岗位，熟悉 React 组件化开发、页面联调与工程协作。",
                "skills": ["React", "TypeScript", "Python", "FastAPI"],
            },
        )
        export_md_response = await client.get(f"/api/v1/resumes/{resume_id}/export?format=markdown")
        export_json_response = await client.get(f"/api/v1/resumes/{resume_id}/export?format=json")
        export_html_response = await client.get(f"/api/v1/resumes/{resume_id}/export?format=html")

    app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert export_md_response.status_code == 200
    assert export_json_response.status_code == 200
    assert export_html_response.status_code == 200

    assert generated["target_job"] == "前端开发"
    assert generated["content"]["skills"][0] == "React"
    assert get_response.json()["student_id"] == "demo_cs_001"
    assert update_response.json()["content"]["summary"].startswith("面向前端开发岗位")
    assert export_md_response.text.startswith("# 张同学")
    assert export_json_response.json()["job_intention"]["target_job"] == "前端开发"
    assert "resume-document" in export_html_response.text


@pytest.mark.asyncio
async def test_resume_get_not_found_returns_404(resume_api_session):
    session, _student_profile_id = resume_api_session
    async with await _build_client(session) as client:
        response = await client.get("/api/v1/resumes/999")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "resume_not_found"
