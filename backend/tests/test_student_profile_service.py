from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.student_profile.models import ResumeRecord, StudentProfileItemRecord, StudentProfileRecord
from app.modules.student_profile.schema import StudentProfileSource, StudentProfileUpdateRequest
from app.modules.student_profile.service import (
    batch_build_student_profiles,
    build_student_profile,
    get_student_profile,
    rebuild_student_profile,
    update_student_profile,
)


@pytest_asyncio.fixture
async def student_session(tmp_path: Path):
    db_path = tmp_path / "student_profile.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_build_student_profile_from_complete_resume(student_session):
    source = StudentProfileSource(
        student_id="stu-001",
        resume_text=(
            "姓名: 张三\n"
            "学校: 上海交通大学\n"
            "专业: 计算机科学与技术\n"
            "学历: 本科\n"
            "2023级\n"
            "熟悉 Python、SQL、FastAPI、Git。\n"
            "项目经历: 校园二手平台项目，负责后端开发与接口设计。\n"
            "实习经历: 在某科技公司担任后端开发实习生，参与需求沟通和交付。\n"
            "竞赛经历: 互联网+省级银奖。\n"
            "学生工作: 曾任学生会部长，负责活动组织与跨部门沟通。\n"
            "求职意向: 后端开发工程师。\n"
            "证书: CET-6。"
        ),
        manual_form={
            "skills": ["Python", "SQL", "FastAPI", "Python"],
            "projects": ["校园二手平台项目"],
        },
        supplement_text="补充说明: 自学 Docker 并完成部署。",
        basic_info={"student_name": "张三", "school": "上海交通大学"},
        resume_filename="zhangsan_resume.txt",
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.student_id == "stu-001"
    assert result.profile.school == "上海交通大学"
    assert result.profile.major in {"计算机科学与技术", "计算机科学"}
    assert result.profile.education == "本科"
    assert "Python" in result.profile.skills
    assert result.profile.skills.count("Python") == 1
    assert result.profile.projects
    assert result.profile.internships
    assert result.profile.competitions
    assert result.profile.student_work
    assert result.profile.resume_source == "hybrid"
    assert isinstance(result.profile.summary, str)
    assert 0 <= result.profile.completeness_score <= 100
    assert 0 <= result.profile.competitiveness_score <= 100
    evidence = result.profile.evidence.model_dump()
    assert isinstance(evidence, dict)
    assert all(isinstance(value, list) for value in evidence.values())
    assert isinstance(result.raw_profile_payload, dict)
    assert result.raw_profile_payload["preprocessed"]["normalized_text"]


@pytest.mark.asyncio
async def test_build_student_profile_from_natural_language_resume(student_session):
    source = StudentProfileSource(
        student_id="stu-natural-001",
        resume_text=(
            "张三，上海交通大学计算机科学与技术专业，本科。"
            "掌握 Python、SQL、React、Docker。"
            "项目经历包括校园二手平台、数据分析看板。"
            "曾在某互联网公司后端开发实习。"
            "求职意向：Python开发工程师。"
        ),
        manual_form={},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.profile.student_name == "张三"
    assert result.profile.school == "上海交通大学"
    assert result.profile.major in {"计算机科学与技术", "计算机科学"}
    assert result.profile.education == "本科"


@pytest.mark.asyncio
async def test_student_name_should_not_fallback_to_major(student_session):
    source = StudentProfileSource(
        student_id="stu-name-001",
        resume_text=(
            "软件工程，广州大学，本科。\n"
            "掌握 Python、SQL。\n"
            "项目经历：教务系统开发。\n"
        ),
        manual_form={},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.profile.student_name == "未明确"
    assert result.profile.major == "软件工程"


@pytest.mark.asyncio
async def test_career_intention_should_only_capture_target_role(student_session):
    source = StudentProfileSource(
        student_id="stu-career-001",
        resume_text=(
            "姓名: 李晨\n"
            "学校: 华南理工大学\n"
            "专业: 软件工程\n"
            "求职意向: 前端开发实习生\n"
            "技能: HTML、CSS、JavaScript、TypeScript\n"
            "项目经历: 校园活动管理系统\n"
        ),
        manual_form={},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.profile.career_intention == "前端开发实习生"
    assert "技能" not in result.profile.career_intention
    assert "项目经历" not in result.profile.career_intention


@pytest.mark.asyncio
async def test_build_student_profile_from_manual_form_only(student_session):
    source = StudentProfileSource(
        student_id="stu-manual-001",
        resume_text="未明确",
        manual_form={
            "student_name": "王五",
            "school": "北京理工大学",
            "major": "信息管理与信息系统",
            "education": "本科",
            "grade": "2022级",
            "skills": ["Excel", "Python", "SQL"],
            "projects": ["学生就业数据分析项目"],
            "internships": ["教育科技公司运营实习"],
            "competitions": ["互联网+校赛金奖"],
            "student_work": ["班长"],
            "career_intention": "数据分析师",
            "certificates": ["CET-6"],
        },
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.profile.resume_source == "manual"
    assert result.profile.school == "北京理工大学"
    assert result.profile.skills == ["Excel", "Python", "SQL"]
    assert result.profile.career_intention == "数据分析师"
    assert result.profile.certificates == ["CET-6"]
    assert result.profile.projects
    assert result.profile.internships


@pytest.mark.asyncio
async def test_build_student_profile_missing_fields_returns_suggestions(student_session):
    source = StudentProfileSource(
        student_id="stu-002",
        resume_text="求职意向: 数据分析实习生。",
        manual_form={},
        supplement_text="未补充其他信息",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.profile.school == "未明确"
    assert result.profile.skills == []
    assert result.profile.certificates == []
    assert result.profile.completeness_score < 60
    assert result.profile.missing_items
    missing_labels = {item.label for item in result.profile.missing_items}
    assert "学校" in missing_labels
    assert "技能" in missing_labels
    assert all(item.suggestion for item in result.profile.missing_items)


@pytest.mark.asyncio
async def test_negative_internship_section_does_not_create_internship(student_session):
    source = StudentProfileSource(
        student_id="stu-no-internship",
        resume_text=(
            "姓名：张伟\n"
            "学校：安徽某职业技术学院\n"
            "专业：计算机应用技术\n"
            "学历：大专\n"
            "求职意向：软件测试实习生 / 技术支持实习生\n"
            "项目经历：\n"
            "项目一：校园课程信息展示页面\n"
            "项目描述：根据课程表内容制作一个简单的网页。\n"
            "实习经历：\n"
            "暂无正式实习经历。\n"
        ),
        manual_form={},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert result.profile.internships == []


@pytest.mark.asyncio
async def test_long_and_repeated_text_keeps_stable_types(student_session):
    repeated = (
        "学校: 华东师范大学。专业: 软件工程。本科。大三。"
        "项目经历: 智能排课系统项目，负责需求分析与实现。"
        "项目经历: 智能排课系统项目，负责需求分析与实现。"
        "实习经历: 在教育科技公司实习，参与沟通与交付。"
        "证书: CET-4。技能: Python, Python, SQL, SQL。"
    ) * 6
    source = StudentProfileSource(student_id="stu-003", resume_text=repeated, manual_form={}, supplement_text="", basic_info={})

    result = await build_student_profile(student_session, source=source, persist=False)

    assert isinstance(result.profile.summary, str)
    assert result.profile.skills.count("Python") == 1
    assert result.profile.skills.count("SQL") == 1
    assert isinstance(result.profile.projects, list)
    assert isinstance(result.profile.internships, list)
    assert isinstance(result.profile.competitions, list)
    assert isinstance(result.profile.student_work, list)
    assert isinstance(result.profile.evidence.model_dump(), dict)
    assert all(isinstance(value, list) for value in result.profile.evidence.model_dump().values())


@pytest.mark.asyncio
async def test_realistic_resume_text_extracts_project_and_internship_sections(student_session):
    source = StudentProfileSource(
        student_id="stu-real-001",
        resume_text=(
            "张晨\n"
            "学校：华南理工大学\n"
            "专业：计算机科学与技术\n"
            "学历：本科\n"
            "求职意向：后端开发工程师 / 数据开发工程师 / 平台工程师\n"
            "专业技能：熟悉 Python、Java、SQL、React、FastAPI、Docker。\n"
            "项目经历：\n"
            "项目一：校园二手交易平台\n"
            "时间：2024.09 - 2024.12\n"
            "角色：后端开发\n"
            "项目描述：面向校内学生的二手商品交易平台。\n"
            "个人职责：使用 FastAPI 设计并开发用户、商品、订单等核心接口。\n"
            "项目二：数据分析看板系统\n"
            "时间：2025.03 - 2025.06\n"
            "角色：全栈开发\n"
            "项目描述：基于业务数据构建可视化分析平台。\n"
            "个人职责：使用 React + TypeScript 搭建前端页面，使用 FastAPI 提供统计分析接口。\n"
            "实习经历：\n"
            "公司：星云软件科技有限公司\n"
            "岗位：后端开发实习生\n"
            "时间：2025.07 - 2025.09\n"
            "工作内容：参与企业内部管理系统的接口开发与维护，编写和优化 SQL，使用 Docker 完成开发环境部署与服务联调。\n"
        ),
        manual_form={},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert len(result.profile.projects) >= 2
    project_names = {item.name for item in result.profile.projects}
    assert "校园二手交易平台" in project_names
    assert "数据分析看板系统" in project_names

    assert len(result.profile.internships) >= 1
    internship = result.profile.internships[0]
    assert internship.company == "星云软件科技有限公司"
    assert internship.role == "后端开发实习生"
    assert "SQL" in internship.description


@pytest.mark.asyncio
async def test_project_result_line_stays_in_current_project_description(student_session):
    source = StudentProfileSource(
        student_id="stu-project-result",
        resume_text=(
            "姓名：李明\n"
            "学校：上海工程技术大学\n"
            "专业：计算机科学与技术\n"
            "学历：本科\n"
            "项目经历：\n"
            "项目一：校园二手交易平台\n"
            "项目描述：面向校内学生的二手商品交易平台。\n"
            "项目成果：通过 Redis 缓存将热门商品接口平均响应时间从约 300ms 降低到约 120ms。\n"
        ),
        manual_form={},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)

    assert len(result.profile.projects) == 1
    assert result.profile.projects[0].name == "校园二手交易平台"
    assert "Redis 缓存" in result.profile.projects[0].description


@pytest.mark.asyncio
async def test_field_type_stability_with_sparse_input(student_session):
    source = StudentProfileSource(
        student_id="stu-type-001",
        resume_text="学校: 南开大学。",
        manual_form={"skills": "Python,SQL", "certificates": None},
        supplement_text="",
        basic_info={},
    )

    result = await build_student_profile(student_session, source=source, persist=False)
    profile = result.profile.model_dump(mode="json")

    assert isinstance(profile["summary"], str)
    assert isinstance(profile["skills"], list)
    assert isinstance(profile["certificates"], list)
    assert isinstance(profile["projects"], list)
    assert isinstance(profile["internships"], list)
    assert isinstance(profile["evidence"], dict)
    assert all(isinstance(value, list) for value in profile["evidence"].values())
    assert profile["career_intention"] == "未明确"


@pytest.mark.asyncio
async def test_persistence_version_increment_and_db_consistency(student_session):
    base_source = StudentProfileSource(
        student_id="stu-004",
        resume_text="学校: 浙江大学。专业: 软件工程。本科。项目经历: 数据平台项目。求职意向: 后端开发。",
        manual_form={"skills": ["Python", "SQL"], "internships": ["某互联网公司后端实习"]},
        supplement_text="证书: CET-6。",
        basic_info={},
    )

    first = await build_student_profile(student_session, source=base_source, persist=True)
    second = await build_student_profile(student_session, source=base_source, persist=True)

    assert first.profile_version == 1
    assert second.profile_version == 2

    profile_count = await student_session.scalar(select(func.count()).select_from(StudentProfileRecord))
    resume_count = await student_session.scalar(select(func.count()).select_from(ResumeRecord))
    item_count = await student_session.scalar(select(func.count()).select_from(StudentProfileItemRecord))

    assert profile_count == 2
    assert resume_count == 2
    assert item_count and item_count > 0

    latest = await get_student_profile(student_session, student_id="stu-004")
    assert latest.profile_version == 2
    assert latest.profile.skills == ["Python", "SQL"]


@pytest.mark.asyncio
async def test_update_rebuild_and_batch_flow(student_session):
    source = StudentProfileSource(
        student_id="stu-005",
        resume_text="学校: 同济大学。专业: 土木工程。本科。项目经历: BIM 协同平台。",
        manual_form={"skills": ["Excel"]},
        supplement_text="求职意向: 产品经理。",
        basic_info={},
    )
    initial = await build_student_profile(student_session, source=source, persist=True)

    updated = await update_student_profile(
        student_session,
        student_id="stu-005",
        request=StudentProfileUpdateRequest(
            manual_form={"skills": ["Excel", "Power BI"], "projects": ["BIM 协同平台"]},
            persist=True,
        ),
    )

    rebuilt = await rebuild_student_profile(student_session, student_id="stu-005", persist=True)
    batch = await batch_build_student_profiles(
        student_session,
        items=[
            StudentProfileSource(student_id="stu-006", resume_text="学校: 复旦大学。专业: 新闻学。本科。", manual_form={"skills": ["沟通"]}, supplement_text="", basic_info={}),
            StudentProfileSource(student_id="stu-007", resume_text="学校: 华中科技大学。专业: 自动化。本科。", manual_form={"skills": ["Python"]}, supplement_text="", basic_info={}),
        ],
        persist=False,
    )

    assert initial.profile_version == 1
    assert updated.profile_version == 2
    assert rebuilt.profile_version == 3
    assert "Power BI" in updated.profile.skills
    assert batch.processed_records == 2
    assert batch.failed_records == 0
