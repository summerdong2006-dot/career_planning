from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.matching.service import get_match_detail, recommend_jobs_for_student, recommend_jobs_for_students_batch
from matching_test_utils import seed_job_profile, seed_student_profile


@pytest_asyncio.fixture
async def matching_session(tmp_path: Path):
    db_path = tmp_path / "matching.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_recommend_jobs_for_student_top_k_and_detail(matching_session):
    student = await seed_student_profile(
        matching_session,
        student_id="stu-service-001",
        summary="熟悉 Python、FastAPI、SQL，完成过后端项目。",
        education="本科",
        skills=["Python", "FastAPI", "SQL"],
        certificates=["CET-6"],
        ability_scores={
            "professional_skills": 82,
            "innovation": 70,
            "learning": 84,
            "stress_tolerance": 68,
            "communication": 76,
            "internship_ability": 66,
        },
        completeness_score=88,
        competitiveness_score=81,
        internships=[{"company": "实验室", "role": "开发"}],
        projects=[{"name": "服务平台"}],
    )
    await seed_job_profile(
        matching_session,
        job_title="后端开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "FastAPI", "SQL"],
        nice_to_have_skills=["Docker"],
        certificates=[],
        soft_skills=["沟通能力", "学习能力"],
        promotion_path=["后端开发工程师", "高级后端开发工程师", "技术负责人"],
        summary="负责 Python 后端开发。",
    )
    await seed_job_profile(
        matching_session,
        job_title="数据分析师",
        education_requirement="本科",
        years_experience_requirement="1-3年",
        must_have_skills=["SQL", "Excel", "Tableau"],
        nice_to_have_skills=[],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=["数据分析师", "高级数据分析师"],
        summary="负责业务数据分析。",
    )
    await matching_session.commit()

    response = await recommend_jobs_for_student(matching_session, student.id, top_k=1, persist=True)

    assert response.student_profile_id == student.id
    assert len(response.matches) == 1
    assert response.matches[0].job_title == "后端开发工程师"
    assert response.matches[0].match_id is not None

    detail = await get_match_detail(matching_session, response.matches[0].match_id)
    assert detail.result.dimension_scores.skill >= 80
    assert detail.result.match_id == response.matches[0].match_id


@pytest.mark.asyncio
async def test_recommend_jobs_for_students_batch(matching_session):
    first = await seed_student_profile(
        matching_session,
        student_id="stu-batch-001",
        summary="Java 后端方向学生。",
        education="本科",
        skills=["Java", "Spring Boot", "SQL"],
        certificates=[],
        ability_scores={
            "professional_skills": 78,
            "innovation": 65,
            "learning": 75,
            "stress_tolerance": 66,
            "communication": 70,
            "internship_ability": 64,
        },
        completeness_score=82,
        competitiveness_score=76,
        internships=[{"company": "软件公司"}],
    )
    second = await seed_student_profile(
        matching_session,
        student_id="stu-batch-002",
        summary="画像字段较少的学生。",
        education="未明确",
        skills=[],
        certificates=[],
        ability_scores={
            "professional_skills": 30,
            "innovation": 35,
            "learning": 40,
            "stress_tolerance": 38,
            "communication": 42,
            "internship_ability": 20,
        },
        completeness_score=28,
        competitiveness_score=33,
        missing_items=[{"field": "skills", "label": "技能", "suggestion": "补充技能"}],
    )
    await seed_job_profile(
        matching_session,
        job_title="Java 开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Java", "Spring Boot"],
        nice_to_have_skills=["Redis"],
        certificates=[],
        soft_skills=["学习能力"],
        promotion_path=["Java 开发工程师", "高级 Java 开发工程师"],
        summary="负责 Java 服务开发。",
        confidence_score=0.3,
    )
    await matching_session.commit()

    response = await recommend_jobs_for_students_batch(
        matching_session,
        [first.id, second.id],
        top_k=1,
        persist=False,
    )

    assert len(response.results) == 2
    assert response.results[0].matches[0].job_title == "Java 开发工程师"
    assert any("岗位画像置信度较低" in risk for risk in response.results[1].matches[0].risk_flags)
    assert any("学生画像完整度较低" in risk for risk in response.results[1].matches[0].risk_flags)




@pytest.mark.asyncio
async def test_computer_student_family_weighting_demotes_admin_and_legal_roles(matching_session):
    student = await seed_student_profile(
        matching_session,
        student_id="stu-family-001",
        summary="计算机专业学生，熟悉 Python、FastAPI、React、MySQL，目标岗位是后端开发工程师。",
        education="本科",
        skills=["Python", "FastAPI", "React", "MySQL", "Redis", "Git"],
        certificates=[],
        ability_scores={
            "professional_skills": 86,
            "innovation": 72,
            "learning": 84,
            "stress_tolerance": 70,
            "communication": 74,
            "internship_ability": 76,
        },
        completeness_score=90,
        competitiveness_score=85,
        internships=[{"company": "科技公司", "role": "后端开发实习生"}],
        projects=[{"name": "职业规划系统"}, {"name": "校园二手交易平台"}],
    )
    await seed_job_profile(
        matching_session,
        job_title="后端开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "FastAPI", "MySQL"],
        nice_to_have_skills=["Redis", "Git"],
        certificates=[],
        soft_skills=["沟通能力", "学习能力"],
        promotion_path=["后端开发工程师", "高级后端开发工程师", "技术负责人"],
        summary="负责 Python 后端接口与数据库开发。",
    )
    await seed_job_profile(
        matching_session,
        job_title="数据分析师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "MySQL", "Excel"],
        nice_to_have_skills=["Tableau"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=["数据分析师", "高级数据分析师"],
        summary="负责业务数据分析与报表建设。",
    )
    await seed_job_profile(
        matching_session,
        job_title="总助/CEO助理",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "React", "MySQL"],
        nice_to_have_skills=["Git"],
        certificates=[],
        soft_skills=["沟通能力", "执行力"],
        promotion_path=["总助/CEO助理", "行政经理"],
        summary="协助管理层推进跨部门事务，要求较强执行力。",
    )
    await seed_job_profile(
        matching_session,
        job_title="律师助理",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "MySQL"],
        nice_to_have_skills=["Git"],
        certificates=[],
        soft_skills=["沟通能力", "细致度"],
        promotion_path=["律师助理", "律师"],
        summary="协助法律文书整理与案件资料支持。",
    )
    await matching_session.commit()

    response = await recommend_jobs_for_student(matching_session, student.id, top_k=4, persist=False)

    top_titles = {item.job_title for item in response.matches[:2]}
    assert top_titles == {"后端开发工程师", "数据分析师"}

    admin_result = next(item for item in response.matches if item.job_title == "总助/CEO助理")
    legal_result = next(item for item in response.matches if item.job_title == "律师助理")
    assert admin_result.total_score < 25
    assert legal_result.total_score < 15
    assert any("岗位族校准" in risk for risk in admin_result.risk_flags)
    assert any("岗位族校准" in risk for risk in legal_result.risk_flags)
