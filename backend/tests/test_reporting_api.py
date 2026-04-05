from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.modules.reporting.models import CareerReportRecord
from matching_test_utils import seed_job_profile, seed_student_profile


@pytest_asyncio.fixture
async def reporting_api_session(tmp_path: Path):
    db_path = tmp_path / "reporting_api.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        student = await seed_student_profile(
            session,
            student_id="stu-report-api-001",
            summary="熟悉 Python、FastAPI、SQL，求职后端开发。",
            education="本科",
            skills=["Python", "FastAPI", "SQL"],
            certificates=[],
            ability_scores={
                "professional_skills": 84,
                "innovation": 72,
                "learning": 82,
                "stress_tolerance": 68,
                "communication": 75,
                "internship_ability": 70,
            },
            completeness_score=86,
            competitiveness_score=81,
            internships=[{"company": "互联网公司"}],
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
            promotion_path=["后端开发工程师", "高级后端开发工程师", "技术负责人"],
            summary="负责 Python 接口和服务开发。",
            job_level="初级",
        )
        await seed_job_profile(
            session,
            job_title="测试开发工程师",
            education_requirement="本科",
            years_experience_requirement="应届/实习可投",
            must_have_skills=["Python", "SQL"],
            nice_to_have_skills=["Docker"],
            certificates=[],
            soft_skills=["沟通能力"],
            promotion_path=["测试开发工程师", "高级测试开发工程师", "测试负责人"],
            summary="负责自动化测试平台开发。",
            job_level="初级",
        )
        await session.commit()
        yield session, student.id, tmp_path
    await engine.dispose()


async def _build_client(session):
    async def override_db():
        yield session

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


async def _generate_report(client: AsyncClient, student_profile_id: int) -> dict:
    response = await client.post(
        "/api/v1/reports/generate",
        json={"student_profile_id": student_profile_id, "top_k": 2},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_generate_report_success(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        response = await client.post(
            "/api/v1/reports/generate",
            json={"student_profile_id": student_profile_id, "top_k": 2},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["student_profile_id"] == student_profile_id
    assert body["content"]["meta"]["student_id"] == "stu-report-api-001"
    assert [section["key"] for section in body["content"]["sections"]] == ["summary", "match", "gap", "plan_short", "plan_mid"]
    assert body["markdown_content"]
    assert "report-document" in body["html_content"]


@pytest.mark.asyncio
async def test_get_report_success(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        response = await client.get(f"/api/v1/reports/{report_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == report_id
    assert body["content"]["meta"]["student_id"] == "stu-report-api-001"
    assert [section["key"] for section in body["content"]["sections"]] == ["summary", "match", "gap", "plan_short", "plan_mid"]


@pytest.mark.asyncio
async def test_get_report_not_found_returns_404(reporting_api_session):
    session, _student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        response = await client.get("/api/v1/reports/999")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "career_report_not_found"


@pytest.mark.asyncio
async def test_put_single_section_success(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        response = await client.put(
            f"/api/v1/reports/{report_id}/sections/gap",
            json={"content": "人工补充：需要增强 Redis 能力。"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    gap_section = next(section for section in body["content"]["sections"] if section["key"] == "gap")
    assert gap_section["content"] == "人工补充：需要增强 Redis 能力。"


@pytest.mark.asyncio
async def test_put_single_section_preserves_line_breaks(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        response = await client.put(
            f"/api/v1/reports/{report_id}/sections/gap",
            json={"content": "第一行\n第二行\n\n第三行"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    gap_section = next(section for section in body["content"]["sections"] if section["key"] == "gap")
    assert gap_section["content"] == "第一行\n第二行\n\n第三行"


@pytest.mark.asyncio
async def test_put_single_section_not_found_returns_error(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        response = await client.put(
            f"/api/v1/reports/{report_id}/sections/unknown_section",
            json={"content": "test"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "career_report_section_not_found"


@pytest.mark.asyncio
async def test_put_report_success_and_get_reflects_changes(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        put_response = await client.put(
            f"/api/v1/reports/{report_id}",
            json={
                "meta": {"target_job": "资深后端开发工程师"},
                "sections": [
                    {"section_key": "summary", "content": "人工改写总体分析。"},
                    {"section_key": "plan_short", "content": "人工改写短期计划。"},
                ],
            },
        )
        get_response = await client.get(f"/api/v1/reports/{report_id}")

    app.dependency_overrides.clear()

    assert put_response.status_code == 200
    assert get_response.status_code == 200

    put_body = put_response.json()
    get_body = get_response.json()
    assert put_body["content"]["meta"]["target_job"] == "资深后端开发工程师"
    assert get_body["content"]["meta"]["target_job"] == "资深后端开发工程师"
    assert next(section for section in get_body["content"]["sections"] if section["key"] == "summary")["content"] == "人工改写总体分析。"
    assert next(section for section in get_body["content"]["sections"] if section["key"] == "plan_short")["content"] == "人工改写短期计划。"


@pytest.mark.asyncio
async def test_put_report_keeps_unmodified_sections(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]
        original_sections = {section["key"]: section["content"] for section in generated["content"]["sections"]}

        put_response = await client.put(
            f"/api/v1/reports/{report_id}",
            json={
                "sections": [
                    {"section_key": "summary", "content": "只修改总体分析"}
                ]
            },
        )

    app.dependency_overrides.clear()

    assert put_response.status_code == 200
    body = put_response.json()
    section_map = {section["key"]: section["content"] for section in body["content"]["sections"]}
    assert section_map["summary"] == "只修改总体分析"
    assert section_map["match"] == original_sections["match"]
    assert section_map["gap"] == original_sections["gap"]
    assert section_map["plan_short"] == original_sections["plan_short"]
    assert section_map["plan_mid"] == original_sections["plan_mid"]


@pytest.mark.asyncio
async def test_export_endpoint_still_works_after_put(reporting_api_session, monkeypatch):
    session, student_profile_id, tmp_path = reporting_api_session
    monkeypatch.setenv("CAREER_REPORT_DOWNLOAD_DIR", tmp_path.as_posix())

    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        put_response = await client.put(
            f"/api/v1/reports/{report_id}",
            json={"sections": [{"section_key": "gap", "content": "人工补充：新的差距说明。"}]},
        )
        export_md_response = await client.get(f"/api/v1/reports/{report_id}/export?format=markdown")
        export_json_response = await client.get(f"/api/v1/reports/{report_id}/export?format=json")
        export_pdf_response = await client.get(f"/api/v1/reports/{report_id}/export?format=pdf")

    app.dependency_overrides.clear()

    assert put_response.status_code == 200
    assert export_md_response.status_code == 200
    assert export_json_response.status_code == 200
    assert export_pdf_response.status_code == 200
    assert "人工补充：新的差距说明。" in export_md_response.text
    assert export_json_response.json()["sections"][2]["content"] == "人工补充：新的差距说明。"
    assert export_pdf_response.headers["content-type"].startswith("application/pdf")
    assert (tmp_path / f"report_{report_id}.pdf").exists()


@pytest.mark.asyncio
async def test_get_and_put_compatible_with_legacy_payload(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        record = await session.get(CareerReportRecord, report_id)
        record.report_payload = {
            "metadata": {
                "student_id": "stu-report-api-001",
                "primary_job_title": "后端开发工程师",
            },
            "executive_summary": "旧结构摘要。",
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
        await session.commit()

        get_response = await client.get(f"/api/v1/reports/{report_id}")
        put_response = await client.put(
            f"/api/v1/reports/{report_id}",
            json={"meta": {"target_job": "新版目标岗位"}},
        )

    app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert [section["key"] for section in get_response.json()["content"]["sections"]] == ["summary", "match", "gap", "plan_short", "plan_mid"]
    assert put_response.status_code == 200
    assert put_response.json()["content"]["meta"]["target_job"] == "新版目标岗位"

    refreshed = await session.get(CareerReportRecord, report_id)
    assert refreshed.report_payload["meta"]["target_job"] == "新版目标岗位"
    assert [section["key"] for section in refreshed.report_payload["sections"]] == ["summary", "match", "gap", "plan_short", "plan_mid"]


@pytest.mark.asyncio
async def test_put_updates_rebuild_fields(reporting_api_session):
    session, student_profile_id, _tmp_path = reporting_api_session
    async with await _build_client(session) as client:
        generated = await _generate_report(client, student_profile_id)
        report_id = generated["report_id"]

        put_response = await client.put(
            f"/api/v1/reports/{report_id}",
            json={
                "meta": {"generated_at": "2026-03-25"},
                "sections": [{"section_key": "gap", "content": "人工补充能力差距。"}],
            },
        )
        get_response = await client.get(f"/api/v1/reports/{report_id}")

    app.dependency_overrides.clear()

    assert put_response.status_code == 200
    put_body = put_response.json()
    get_body = get_response.json()
    assert "人工补充能力差距。" in put_body["markdown_content"]
    assert "report-document" in put_body["html_content"]
    assert put_body["completeness_check"]["checks"]
    assert get_body["content"]["meta"]["generated_at"] == "2026-03-25"

