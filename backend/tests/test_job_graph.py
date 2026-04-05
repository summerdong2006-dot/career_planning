from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.job_graph import build_job_graph, find_related_jobs, generate_career_paths
from app.services.job_similarity import compute_job_similarity
from matching_test_utils import seed_job_profile


@pytest_asyncio.fixture
async def career_graph_session(tmp_path: Path):
    db_path = tmp_path / "career_graph.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_career_jobs(career_graph_session):
    jobs = {}
    job_specs = [
        {
            "job_title": "初级后端开发工程师",
            "job_level": "初级",
            "must_have_skills": ["Python", "FastAPI", "SQL"],
            "nice_to_have_skills": ["Docker", "Git"],
            "promotion_path": ["初级后端开发工程师", "中级后端开发工程师", "高级后端开发工程师"],
            "summary": "负责 Python 后端接口开发与数据库设计。",
        },
        {
            "job_title": "中级后端开发工程师",
            "job_level": "中级",
            "must_have_skills": ["Python", "FastAPI", "SQL", "Redis"],
            "nice_to_have_skills": ["Docker", "Git"],
            "promotion_path": ["中级后端开发工程师", "高级后端开发工程师", "技术负责人"],
            "summary": "负责核心服务研发、缓存设计与性能优化。",
        },
        {
            "job_title": "高级后端开发工程师",
            "job_level": "高级",
            "must_have_skills": ["Python", "FastAPI", "SQL", "Redis"],
            "nice_to_have_skills": ["Docker", "Kubernetes"],
            "promotion_path": ["高级后端开发工程师", "技术负责人", "架构师"],
            "summary": "负责高并发服务架构设计与稳定性治理。",
        },
        {
            "job_title": "Java开发工程师",
            "job_level": "初级",
            "must_have_skills": ["Java", "Spring Boot", "SQL"],
            "nice_to_have_skills": ["Redis", "Git"],
            "promotion_path": ["Java开发工程师", "高级Java开发工程师", "技术负责人"],
            "summary": "负责 Java 微服务开发。",
        },
        {
            "job_title": "测试开发工程师",
            "job_level": "初级",
            "must_have_skills": ["Python", "SQL", "Git"],
            "nice_to_have_skills": ["Docker"],
            "promotion_path": ["测试开发工程师", "高级测试开发工程师", "测试负责人"],
            "summary": "负责自动化测试平台与质量工程建设。",
        },
        {
            "job_title": "数据工程师",
            "job_level": "中级",
            "must_have_skills": ["Python", "SQL", "Spark"],
            "nice_to_have_skills": ["Hive", "ETL"],
            "promotion_path": ["数据工程师", "高级数据工程师", "数据平台主管"],
            "summary": "负责离线数仓与数据链路建设。",
        },
        {
            "job_title": "高级数据工程师",
            "job_level": "高级",
            "must_have_skills": ["Python", "SQL", "Spark"],
            "nice_to_have_skills": ["Hive", "ETL", "Docker"],
            "promotion_path": ["高级数据工程师", "数据平台主管", "数据架构师"],
            "summary": "负责大规模数据平台建设与调优。",
        },
        {
            "job_title": "数据分析师",
            "job_level": "初级",
            "must_have_skills": ["SQL", "Excel", "Tableau"],
            "nice_to_have_skills": ["Python", "Power BI"],
            "promotion_path": ["数据分析师", "高级数据分析师", "数据产品经理"],
            "summary": "负责经营分析与业务洞察。",
        },
        {
            "job_title": "AI工程师",
            "job_level": "中级",
            "must_have_skills": ["Python", "机器学习", "SQL"],
            "nice_to_have_skills": ["PyTorch", "NLP"],
            "promotion_path": ["AI工程师", "高级AI工程师", "算法负责人"],
            "summary": "负责机器学习模型训练与落地。",
        },
        {
            "job_title": "运维开发工程师",
            "job_level": "中级",
            "must_have_skills": ["Python", "Linux", "Docker", "Kubernetes"],
            "nice_to_have_skills": ["Git", "SQL"],
            "promotion_path": ["运维开发工程师", "高级运维开发工程师", "平台负责人"],
            "summary": "负责平台运维自动化与容器化平台建设。",
        },
    ]

    for spec in job_specs:
        profile = await seed_job_profile(
            career_graph_session,
            job_title=spec["job_title"],
            education_requirement="本科",
            years_experience_requirement="应届/实习可投" if spec["job_level"] == "初级" else "1-3年",
            must_have_skills=spec["must_have_skills"],
            nice_to_have_skills=spec["nice_to_have_skills"],
            certificates=[],
            soft_skills=["沟通能力", "学习能力"],
            promotion_path=spec["promotion_path"],
            summary=spec["summary"],
            job_level=spec["job_level"],
        )
        jobs[spec["job_title"]] = profile

    await career_graph_session.commit()
    return jobs


@pytest.mark.asyncio
async def test_similarity_is_symmetric(seeded_career_jobs):
    junior_backend = seeded_career_jobs["初级后端开发工程师"]
    data_engineer = seeded_career_jobs["数据工程师"]

    left_to_right = compute_job_similarity(junior_backend, data_engineer)
    right_to_left = compute_job_similarity(data_engineer, junior_backend)

    assert left_to_right == right_to_left
    assert 0 <= left_to_right <= 100


@pytest.mark.asyncio
async def test_find_related_jobs_sorted_correctly(career_graph_session, seeded_career_jobs):
    target_job_id = seeded_career_jobs["初级后端开发工程师"].source_clean_id

    related_jobs = await find_related_jobs(career_graph_session, target_job_id, top_k=5)

    assert len(related_jobs) == 5
    assert related_jobs[0]["job_title"] == "中级后端开发工程师"
    assert related_jobs == sorted(related_jobs, key=lambda item: (-item["similarity"], item["job_id"]))


@pytest.mark.asyncio
async def test_each_job_has_at_least_two_paths(career_graph_session, seeded_career_jobs):
    tracked_titles = [
        "初级后端开发工程师",
        "中级后端开发工程师",
        "高级后端开发工程师",
        "Java开发工程师",
        "数据工程师",
    ]

    generated = 0
    for title in tracked_titles:
        response = await generate_career_paths(career_graph_session, seeded_career_jobs[title].source_clean_id)
        assert response["job_id"] == seeded_career_jobs[title].source_clean_id
        assert len(response["paths"]) >= 2
        generated += 1

    assert generated >= 5


@pytest.mark.asyncio
async def test_generated_paths_have_valid_length(career_graph_session, seeded_career_jobs):
    tracked_titles = [
        "初级后端开发工程师",
        "中级后端开发工程师",
        "高级后端开发工程师",
        "Java开发工程师",
        "数据工程师",
    ]

    for title in tracked_titles:
        response = await generate_career_paths(career_graph_session, seeded_career_jobs[title].source_clean_id)
        for path in response["paths"]:
            assert len(path) >= 2
            assert path[0] == title


@pytest.mark.asyncio
async def test_build_job_graph_nodes_and_edges_are_valid(career_graph_session, seeded_career_jobs):
    job_ids = [profile.source_clean_id for profile in seeded_career_jobs.values()]

    graph = await build_job_graph(career_graph_session, job_ids)

    node_ids = {node["job_id"] for node in graph["nodes"]}
    assert len(graph["nodes"]) >= 10
    assert set(job_ids).issubset(node_ids)
    assert graph["edges"]
    assert {edge["type"] for edge in graph["edges"]} == {"promotion", "transition"}
    assert sum(1 for edge in graph["edges"] if edge["type"] == "promotion") > 0
    assert sum(1 for edge in graph["edges"] if edge["type"] == "transition") > 0
    assert all(edge["source_job_id"] in node_ids for edge in graph["edges"])
    assert all(edge["target_job_id"] in node_ids for edge in graph["edges"])
    assert all(0 <= edge["weight"] <= 100 for edge in graph["edges"])


@pytest.mark.asyncio
async def test_build_job_graph_creates_promotion_edges_from_profile_path_text(career_graph_session):
    target = await seed_job_profile(
        career_graph_session,
        job_title="运营专员",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "沟通"],
        nice_to_have_skills=["SQL"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=["运营专员", "运营主管", "运营经理"],
        summary="负责基础运营执行。",
        job_level="初级",
    )
    related = await seed_job_profile(
        career_graph_session,
        job_title="市场专员",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "沟通"],
        nice_to_have_skills=["SQL"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=["市场专员", "市场主管"],
        summary="负责市场活动执行。",
        job_level="初级",
    )
    await career_graph_session.commit()

    graph = await build_job_graph(career_graph_session, [target.source_clean_id, related.source_clean_id])

    promotion_edges = [edge for edge in graph["edges"] if edge["type"] == "promotion"]
    node_ids = {node["job_id"] for node in graph["nodes"]}

    assert len(promotion_edges) >= 2
    assert any(edge["source_job_id"] == target.source_clean_id for edge in promotion_edges)
    assert any(str(edge["target_job_id"]).startswith("promotion::") for edge in promotion_edges)
    assert all(edge["source_job_id"] in node_ids for edge in promotion_edges)
    assert all(edge["target_job_id"] in node_ids for edge in promotion_edges)


@pytest.mark.asyncio
async def test_generate_career_paths_backfills_with_similar_jobs(career_graph_session):
    target = await seed_job_profile(
        career_graph_session,
        job_title="内容运营",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "SQL"],
        nice_to_have_skills=[],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=[],
        summary="负责内容运营与数据分析。",
        job_level="初级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="活动运营",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "SQL"],
        nice_to_have_skills=["Power BI"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=[],
        summary="负责活动运营。",
        job_level="初级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="用户运营",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "SQL"],
        nice_to_have_skills=["Python"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=[],
        summary="负责用户增长与留存。",
        job_level="初级",
    )
    await career_graph_session.commit()

    result = await generate_career_paths(career_graph_session, target.source_clean_id)

    assert len(result["paths"]) >= 1
    assert all(path[0] == "内容运营" for path in result["paths"])
    assert all(len(path) >= 2 for path in result["paths"])


@pytest.mark.asyncio
async def test_generate_career_paths_avoids_admin_to_tech_paths(career_graph_session):
    admin_target = await seed_job_profile(
        career_graph_session,
        job_title="总助/CEO助理",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "沟通"],
        nice_to_have_skills=["Python"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=[],
        summary="负责管理层事务协调与日程支持。",
        job_level="初级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="行政助理",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Excel", "沟通"],
        nice_to_have_skills=["文档处理"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=[],
        summary="负责行政协同与流程跟进。",
        job_level="初级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="后端开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "SQL"],
        nice_to_have_skills=["Git"],
        certificates=[],
        soft_skills=["学习能力"],
        promotion_path=[],
        summary="负责后端接口开发。",
        job_level="初级",
    )
    await career_graph_session.commit()

    result = await generate_career_paths(career_graph_session, admin_target.source_clean_id)

    flattened_titles = [title for path in result["paths"] for title in path]
    assert "后端开发工程师" not in flattened_titles


@pytest.mark.asyncio
async def test_generate_career_paths_for_tech_target_prefers_technical_families(career_graph_session):
    target = await seed_job_profile(
        career_graph_session,
        job_title="后端开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "FastAPI", "SQL"],
        nice_to_have_skills=["Redis"],
        certificates=[],
        soft_skills=["学习能力"],
        promotion_path=[],
        summary="负责 Python 后端开发。",
        job_level="初级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="数据工程师",
        education_requirement="本科",
        years_experience_requirement="1-3年",
        must_have_skills=["Python", "SQL", "ETL"],
        nice_to_have_skills=["Redis"],
        certificates=[],
        soft_skills=["学习能力"],
        promotion_path=[],
        summary="负责数据链路建设。",
        job_level="中级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="Java开发工程师",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Java", "SQL"],
        nice_to_have_skills=["Git"],
        certificates=[],
        soft_skills=["学习能力"],
        promotion_path=[],
        summary="负责 Java 服务开发。",
        job_level="初级",
    )
    await seed_job_profile(
        career_graph_session,
        job_title="总助/CEO助理",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "SQL"],
        nice_to_have_skills=["沟通"],
        certificates=[],
        soft_skills=["沟通能力"],
        promotion_path=[],
        summary="负责事务协调。",
        job_level="初级",
    )
    await career_graph_session.commit()

    result = await generate_career_paths(career_graph_session, target.source_clean_id)

    flattened_titles = [title for path in result["paths"] for title in path]
    assert "总助/CEO助理" not in flattened_titles
    assert any(title in {"数据工程师", "Java开发工程师"} for title in flattened_titles)
