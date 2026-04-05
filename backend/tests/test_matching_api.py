from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from matching_test_utils import seed_job_profile, seed_student_profile


@pytest_asyncio.fixture
async def matching_api_session(tmp_path: Path):
    db_path = tmp_path / "matching_api.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        student = await seed_student_profile(
            session,
            student_id="stu-api-001",
            summary="熟悉 Python、FastAPI、SQL。",
            education="本科",
            skills=["Python", "FastAPI", "SQL"],
            certificates=["CET-6"],
            ability_scores={
                "professional_skills": 84,
                "innovation": 72,
                "learning": 83,
                "stress_tolerance": 68,
                "communication": 78,
                "internship_ability": 70,
            },
            completeness_score=87,
            competitiveness_score=80,
            internships=[{"company": "科技公司"}],
        )
        second = await seed_student_profile(
            session,
            student_id="stu-api-002",
            summary="熟悉 Java、Spring Boot。",
            education="本科",
            skills=["Java", "Spring Boot"],
            certificates=[],
            ability_scores={
                "professional_skills": 79,
                "innovation": 66,
                "learning": 77,
                "stress_tolerance": 60,
                "communication": 74,
                "internship_ability": 64,
            },
            completeness_score=80,
            competitiveness_score=75,
        )
        await seed_job_profile(
            session,
            job_title="后端开发工程师",
            education_requirement="本科",
            years_experience_requirement="应届/实习可投",
            must_have_skills=["Python", "FastAPI", "SQL"],
            nice_to_have_skills=["Docker"],
            certificates=[],
            soft_skills=["沟通能力", "学习能力"],
            promotion_path=["后端开发工程师", "高级后端开发工程师"],
            summary="负责 Python 后端开发。",
        )
        await seed_job_profile(
            session,
            job_title="Java 开发工程师",
            education_requirement="本科",
            years_experience_requirement="应届/实习可投",
            must_have_skills=["Java", "Spring Boot"],
            nice_to_have_skills=["SQL"],
            certificates=[],
            soft_skills=["学习能力"],
            promotion_path=["Java 开发工程师", "高级 Java 开发工程师"],
            summary="负责 Java 服务开发。",
        )
        await session.commit()
        yield session, student.id, second.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_matching_recommend_batch_and_detail_api(matching_api_session):
    session, first_student_id, second_student_id = matching_api_session

    async def override_db():
        yield session

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        recommend_response = await client.post(
            "/api/v1/matching/recommend",
            json={"student_profile_id": first_student_id, "top_k": 2},
        )
        batch_response = await client.post(
            "/api/v1/matching/recommend-batch",
            json={"student_profile_ids": [first_student_id, second_student_id], "top_k": 1, "persist": False},
        )

    app.dependency_overrides.clear()

    assert recommend_response.status_code == 200
    recommend_body = recommend_response.json()
    assert recommend_body["student_profile_id"] == first_student_id
    assert len(recommend_body["matches"]) == 2
    assert recommend_body["matches"][0]["dimension_scores"]["skill"] >= 80

    match_id = recommend_body["matches"][0]["match_id"]
    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        detail_response = await client.get(f"/api/v1/matching/{match_id}")
    app.dependency_overrides.clear()

    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["match_id"] == match_id
    assert detail_body["result"]["dimension_details"]["skill"]["details"]["must_matches"]

    assert batch_response.status_code == 200
    batch_body = batch_response.json()
    assert len(batch_body["results"]) == 2
    assert batch_body["results"][1]["student_profile_id"] == second_student_id

