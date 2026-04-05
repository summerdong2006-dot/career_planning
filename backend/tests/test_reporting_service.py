from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import AppException
from app.db.base import Base
from app.modules.reporting.models import CareerReportRecord
from app.modules.reporting.schema import (
    CareerReportGenerateRequest,
    CareerReportMetaUpdate,
    CareerReportPutRequest,
    CareerReportSectionPutRequest,
    CareerReportSectionUpdate,
)
from app.modules.reporting.service import (
    generate_career_report,
    get_career_report,
    put_career_report,
    update_career_report_section,
)
from matching_test_utils import seed_job_profile, seed_student_profile


@pytest_asyncio.fixture
async def reporting_session(tmp_path: Path):
    db_path = tmp_path / "reporting.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_reporting_data(reporting_session):
    student = await seed_student_profile(
        reporting_session,
        student_id="stu-report-001",
        summary="熟悉 Python、FastAPI、SQL，做过校园项目和后端实习。",
        education="本科",
        skills=["Python", "FastAPI", "SQL", "Docker"],
        certificates=["CET-6"],
        ability_scores={
            "professional_skills": 86,
            "innovation": 74,
            "learning": 84,
            "stress_tolerance": 70,
            "communication": 79,
            "internship_ability": 76,
        },
        completeness_score=88,
        competitiveness_score=83,
        missing_items=[{"field": "projects", "label": "项目成果", "suggestion": "补充量化项目结果和系统规模描述"}],
        internships=[{"company": "科技公司", "role": "后端实习生"}],
        projects=[{"name": "排课系统", "role": "后端开发"}],
    )
    await seed_job_profile(
        reporting_session,
        job_title="后端开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "FastAPI", "SQL"],
        nice_to_have_skills=["Docker", "Redis"],
        certificates=[],
        soft_skills=["沟通能力", "学习能力"],
        promotion_path=["后端开发工程师", "高级后端开发工程师", "技术负责人"],
        summary="负责 Python 服务开发与接口设计。",
        job_level="初级",
    )
    await seed_job_profile(
        reporting_session,
        job_title="测试开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "SQL", "Git"],
        nice_to_have_skills=["Docker"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=["测试开发工程师", "高级测试开发工程师", "测试负责人"],
        summary="负责自动化测试开发。",
        job_level="初级",
    )
    await seed_job_profile(
        reporting_session,
        job_title="数据工程师",
        education_requirement="本科",
        years_experience_requirement="1-3年",
        must_have_skills=["Python", "SQL", "Spark"],
        nice_to_have_skills=["ETL"],
        certificates=[],
        soft_skills=["学习能力"],
        promotion_path=["数据工程师", "高级数据工程师", "数据架构师"],
        summary="负责数据链路和数仓开发。",
        job_level="中级",
    )
    await reporting_session.commit()
    return student


async def _create_report(reporting_session, student_id: int):
    return await generate_career_report(
        reporting_session,
        CareerReportGenerateRequest(student_profile_id=student_id, top_k=3, persist=True),
    )


@pytest.mark.asyncio
async def test_get_career_report_success(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)

    report = await get_career_report(reporting_session, created.report_id)

    assert report.report_id == created.report_id
    assert report.content.meta.student_id == "stu-report-001"
    assert [section.key for section in report.content.sections] == ["summary", "match", "gap", "plan_short", "plan_mid"]


@pytest.mark.asyncio
async def test_get_career_report_not_found(reporting_session):
    with pytest.raises(AppException) as exc_info:
        await get_career_report(reporting_session, 999)

    assert exc_info.value.error_code == "career_report_not_found"


@pytest.mark.asyncio
async def test_update_single_section_success(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)

    updated = await update_career_report_section(
        reporting_session,
        created.report_id,
        "gap",
        CareerReportSectionPutRequest(content="人工补充：需要加强 Redis 和缓存设计能力。"),
    )

    gap_section = next(section for section in updated.content.sections if section.key == "gap")
    assert gap_section.content == "人工补充：需要加强 Redis 和缓存设计能力。"
    assert "Redis" in updated.markdown_content
    assert "report-document" in updated.html_content


@pytest.mark.asyncio
async def test_update_single_section_preserves_line_breaks(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)
    multiline_content = "第一行\n第二行\n\n第三行"

    updated = await update_career_report_section(
        reporting_session,
        created.report_id,
        "gap",
        CareerReportSectionPutRequest(content=multiline_content),
    )

    gap_section = next(section for section in updated.content.sections if section.key == "gap")
    assert gap_section.content == multiline_content
    assert "第一行\n第二行\n\n第三行" in updated.markdown_content


@pytest.mark.asyncio
async def test_update_single_section_not_found(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)

    with pytest.raises(AppException) as exc_info:
        await update_career_report_section(
            reporting_session,
            created.report_id,
            "unknown_section",
            CareerReportSectionPutRequest(content="test"),
        )

    assert exc_info.value.error_code == "career_report_section_not_found"


@pytest.mark.asyncio
async def test_put_report_updates_meta(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)

    updated = await put_career_report(
        reporting_session,
        created.report_id,
        CareerReportPutRequest(
            meta=CareerReportMetaUpdate(target_job="资深后端开发工程师", generated_at="2026-03-25"),
        ),
    )

    assert updated.content.meta.student_id == "stu-report-001"
    assert updated.content.meta.target_job == "资深后端开发工程师"
    assert updated.content.meta.generated_at == "2026-03-25"


@pytest.mark.asyncio
async def test_put_report_updates_partial_sections(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)

    updated = await put_career_report(
        reporting_session,
        created.report_id,
        CareerReportPutRequest(
            sections=[
                CareerReportSectionUpdate(section_key="summary", content="人工改写总体分析。"),
                CareerReportSectionUpdate(section_key="plan_short", content="人工改写短期计划。"),
            ]
        ),
    )

    section_map = {section.key: section for section in updated.content.sections}
    assert section_map["summary"].content == "人工改写总体分析。"
    assert section_map["plan_short"].content == "人工改写短期计划。"


@pytest.mark.asyncio
async def test_put_report_keeps_unmodified_sections(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)
    original_section_map = {section.key: section.content for section in created.content.sections}

    updated = await put_career_report(
        reporting_session,
        created.report_id,
        CareerReportPutRequest(
            sections=[CareerReportSectionUpdate(section_key="summary", content="只修改总体分析")]
        ),
    )

    updated_section_map = {section.key: section.content for section in updated.content.sections}
    assert updated_section_map["summary"] == "只修改总体分析"
    assert updated_section_map["match"] == original_section_map["match"]
    assert updated_section_map["gap"] == original_section_map["gap"]
    assert updated_section_map["plan_short"] == original_section_map["plan_short"]
    assert updated_section_map["plan_mid"] == original_section_map["plan_mid"]


@pytest.mark.asyncio
async def test_put_report_legacy_payload_rewrites_to_standard_structure(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)
    record = await reporting_session.get(CareerReportRecord, created.report_id)
    record.report_payload = {
        "metadata": {
            "student_id": "stu-report-001",
            "primary_job_title": "后端开发工程师",
        },
        "executive_summary": "这是旧结构摘要。",
        "sections": [
            {"key": "overview", "title": "职业发展总览", "summary": "旧结构总体分析"},
            {"key": "job_recommendations", "title": "岗位推荐", "body_markdown": "旧结构岗位推荐"},
            {"key": "risk_alerts", "title": "风险提示", "summary": "旧结构风险提示"},
            {"key": "action_plan", "title": "行动计划", "summary": "旧结构短期计划"},
            {"key": "career_paths", "title": "职业路径", "summary": "旧结构中期计划"},
        ],
    }
    record.editor_state = {}
    record.completeness_check = {}
    record.markdown_content = ""
    record.html_content = ""
    await reporting_session.commit()

    updated = await put_career_report(
        reporting_session,
        created.report_id,
        CareerReportPutRequest(meta=CareerReportMetaUpdate(target_job="新版目标岗位")),
    )

    refreshed = await reporting_session.get(CareerReportRecord, created.report_id)
    assert refreshed.report_payload["meta"]["target_job"] == "新版目标岗位"
    assert [section["key"] for section in refreshed.report_payload["sections"]] == ["summary", "match", "gap", "plan_short", "plan_mid"]
    assert updated.content.meta.target_job == "新版目标岗位"


@pytest.mark.asyncio
async def test_update_rebuilds_markdown_html_and_completeness(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)
    before = await get_career_report(reporting_session, created.report_id)

    updated = await put_career_report(
        reporting_session,
        created.report_id,
        CareerReportPutRequest(
            sections=[CareerReportSectionUpdate(section_key="gap", content="人工补充能力差距。")],
            meta=CareerReportMetaUpdate(generated_at="2026-03-25"),
        ),
    )

    assert updated.markdown_content != before.markdown_content
    assert "人工补充能力差距。" in updated.markdown_content
    assert updated.html_content != before.html_content
    assert "report-document" in updated.html_content
    assert updated.completeness_check.score >= 0
    assert isinstance(updated.completeness_check.missing_sections, list)
    assert updated.completeness_check.checks


@pytest.mark.asyncio
async def test_put_report_updates_report_title_and_status(reporting_session, seeded_reporting_data):
    created = await _create_report(reporting_session, seeded_reporting_data.id)

    updated = await put_career_report(
        reporting_session,
        created.report_id,
        CareerReportPutRequest(report_title="新的职业报告", status="reviewed"),
    )

    assert updated.report_title == "新的职业报告"
    assert updated.status == "reviewed"
