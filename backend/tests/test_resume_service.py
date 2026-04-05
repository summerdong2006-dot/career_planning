from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.resumes.service import export_resume, generate_resume, get_resume, update_resume
from app.modules.resumes.schema import ResumeGenerateRequest, ResumeUpdateRequest
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
async def resume_service_session(tmp_path: Path):
    db_path = tmp_path / "resume_service.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        student = await _seed_student_profile(session)
        await session.commit()
        yield session, student.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_resume_persisted_and_targeted(resume_service_session):
    session, student_profile_id = resume_service_session

    result = await generate_resume(
        session,
        ResumeGenerateRequest(
            student_profile_id=student_profile_id,
            target_job="前端开发",
            style="campus",
            persist=True,
        ),
    )

    assert result.resume_id > 0
    assert result.student_profile_id == student_profile_id
    assert result.target_job == "前端开发"
    assert result.style == "campus"
    assert result.content.job_intention.target_city == "深圳"
    assert result.content.skills[:1] == ["React"]
    assert "Card5" not in result.markdown_content
    assert "Card6" not in result.markdown_content
    assert "report-document" not in result.html_content
    assert "React" in result.markdown_content


@pytest.mark.asyncio
async def test_update_resume_and_export_json(resume_service_session):
    session, student_profile_id = resume_service_session
    generated = await generate_resume(
        session,
        ResumeGenerateRequest(
            student_profile_id=student_profile_id,
            target_job="后端开发",
            style="campus",
            persist=True,
        ),
    )

    updated = await update_resume(
        session,
        generated.resume_id,
        ResumeUpdateRequest(
            summary="面向后端开发岗位，具备 Python、FastAPI、MySQL、Redis 项目实践和实习经历。",
            extras=["CET-6", "具备良好的代码协作习惯"],
        ),
    )
    exported = await export_resume(session, generated.resume_id, "json")
    fetched = await get_resume(session, generated.resume_id)

    assert updated.resume_id == generated.resume_id
    assert updated.content.summary.startswith("面向后端开发岗位")
    assert updated.content.extras == ["CET-6", "具备良好的代码协作习惯"]
    assert exported.format == "json"
    assert exported.content["summary"].startswith("面向后端开发岗位")
    assert fetched.content.summary == updated.content.summary
