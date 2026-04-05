import pytest

from app.modules.matching.matcher import (
    classify_match_category,
    group_top_k_jobs_for_student,
    match_student_to_job,
    rank_jobs_for_student,
)
from app.modules.matching.schema import JobMatchProfile, StudentMatchProfile


@pytest.fixture
def matcher_student() -> StudentMatchProfile:
    return StudentMatchProfile(
        student_profile_id=1,
        student_id="stu-matcher-001",
        summary="熟悉 Python、FastAPI、SQL，有后端项目经历。",
        education="本科",
        career_intention="后端开发工程师",
        professional_skills=["Python", "FastAPI", "SQL", "Git"],
        certificates=["CET-6"],
        innovation_score=72,
        learning_score=82,
        stress_score=68,
        communication_score=75,
        internship_score=66,
        professional_skill_score=80,
        completeness_score=86,
        competitiveness_score=78,
        internship_count=1,
        project_count=2,
        extracted_evidence={
            "summary": ["熟悉 Python、FastAPI、SQL"],
            "skills": ["项目中使用 Python 和 FastAPI 开发接口"],
            "learning": ["自学后端框架"],
            "communication": ["负责项目汇报"],
        },
    )


@pytest.fixture
def matcher_jobs() -> list[JobMatchProfile]:
    return [
        JobMatchProfile(
            job_profile_id=11,
            job_id=101,
            job_title="后端开发工程师",
            education_requirement="本科",
            years_experience_requirement="应届/实习可投",
            must_have_skills=["Python", "FastAPI", "SQL"],
            nice_to_have_skills=["Docker"],
            certificates=[],
            soft_skills=["沟通能力", "学习能力"],
            promotion_path=["后端开发工程师", "高级后端开发工程师"],
            summary="负责后端开发，要求 Python / FastAPI / SQL。",
            extracted_evidence={"summary": ["负责后端开发，要求 Python / FastAPI / SQL。"]},
            confidence_score=92,
        ),
        JobMatchProfile(
            job_profile_id=12,
            job_id=102,
            job_title="数据开发工程师",
            education_requirement="本科",
            years_experience_requirement="1-3年",
            must_have_skills=["Python", "SQL", "Spark"],
            nice_to_have_skills=["Hive"],
            certificates=[],
            soft_skills=["沟通能力"],
            promotion_path=["数据开发工程师", "高级数据开发工程师"],
            summary="负责离线数据开发，要求 Spark。",
            extracted_evidence={"summary": ["负责离线数据开发，要求 Spark。"]},
            confidence_score=88,
        ),
        JobMatchProfile(
            job_profile_id=13,
            job_id=103,
            job_title="Java 开发工程师",
            education_requirement="本科",
            years_experience_requirement="应届/实习可投",
            must_have_skills=["Java", "Spring Boot"],
            nice_to_have_skills=["Redis"],
            certificates=[],
            soft_skills=["学习能力"],
            promotion_path=["Java 开发工程师", "高级 Java 开发工程师"],
            summary="负责 Java 服务开发。",
            extracted_evidence={"summary": ["负责 Java 服务开发。"]},
            confidence_score=86,
        ),
    ]


@pytest.fixture
def category_student() -> StudentMatchProfile:
    return StudentMatchProfile(
        student_profile_id=10,
        student_id="stu-category-001",
        summary="技能覆盖较强，适合做推荐分层测试。",
        education="本科",
        career_intention="后端开发工程师",
        professional_skills=["Python", "FastAPI", "SQL", "Docker", "Git"],
        certificates=["CET-6"],
        innovation_score=85,
        learning_score=90,
        stress_score=82,
        communication_score=88,
        internship_score=85,
        professional_skill_score=92,
        completeness_score=95,
        competitiveness_score=93,
        internship_count=2,
        project_count=3,
        extracted_evidence={"summary": ["强匹配样本"]},
    )


@pytest.fixture
def category_jobs() -> list[JobMatchProfile]:
    return [
        JobMatchProfile(
            job_profile_id=201,
            job_id=201,
            job_title="Safe岗",
            education_requirement="本科",
            years_experience_requirement="应届/实习可投",
            must_have_skills=["Python", "FastAPI", "SQL"],
            nice_to_have_skills=["Docker"],
            certificates=[],
            soft_skills=["沟通能力", "学习能力"],
            promotion_path=["Safe岗", "高级 Safe岗"],
            summary="safe",
            confidence_score=95,
        ),
        JobMatchProfile(
            job_profile_id=202,
            job_id=202,
            job_title="Match岗",
            education_requirement="本科",
            years_experience_requirement="1-3年",
            must_have_skills=["Python", "SQL", "Spark"],
            nice_to_have_skills=["Docker"],
            certificates=[],
            soft_skills=["沟通能力"],
            promotion_path=["Match岗", "高级 Match岗"],
            summary="match",
            confidence_score=90,
        ),
        JobMatchProfile(
            job_profile_id=203,
            job_id=203,
            job_title="Stretch岗",
            education_requirement="本科",
            years_experience_requirement="1-3年",
            must_have_skills=["Python", "Redis", "Kubernetes"],
            nice_to_have_skills=["Docker"],
            certificates=[],
            soft_skills=["沟通能力"],
            promotion_path=["Stretch岗", "高级 Stretch岗"],
            summary="stretch",
            confidence_score=90,
        ),
    ]



def test_matcher_top_k_sorting(matcher_student, matcher_jobs):
    results = rank_jobs_for_student(matcher_student, matcher_jobs, top_k=2)

    assert len(results) == 2
    assert results[0].job_title == "后端开发工程师"
    assert results[0].total_score >= results[1].total_score



def test_matcher_empty_fields_tolerated():
    student = StudentMatchProfile(student_profile_id=2)
    jobs = [JobMatchProfile(job_profile_id=21, job_id=201, job_title="通用岗位")]

    results = rank_jobs_for_student(student, jobs, top_k=3)

    assert len(results) == 1
    assert results[0].job_title == "通用岗位"
    assert isinstance(results[0].gap_analysis, list)
    assert isinstance(results[0].risk_flags, list)



def test_matcher_risk_flags_trigger():
    student = StudentMatchProfile(
        student_profile_id=3,
        professional_skills=["Python"],
        completeness_score=30,
        learning_score=55,
        communication_score=50,
        professional_skill_score=48,
    )
    job = JobMatchProfile(
        job_profile_id=31,
        job_id=301,
        job_title="平台开发工程师",
        education_requirement="本科",
        years_experience_requirement="1-3年",
        must_have_skills=["Python", "Redis"],
        nice_to_have_skills=["Docker"],
        soft_skills=["沟通能力"],
        summary="要求 Python、Redis。",
        confidence_score=30,
    )

    result = match_student_to_job(student, job)

    assert any("must_have" in item for item in result.risk_flags)
    assert any("完整度较低" in item for item in result.risk_flags)
    assert any("confidence_score 低" in item for item in result.risk_flags)
    assert any("缺少核心技能：Redis" in item for item in result.gap_analysis)



def test_matcher_category_classification(category_student, category_jobs):
    results = [match_student_to_job(category_student, job) for job in category_jobs]
    categories = {result.job_title: classify_match_category(result) for result in results}

    assert categories["Safe岗"] == "safe"
    assert categories["Match岗"] == "match"
    assert categories["Stretch岗"] == "stretch"



def test_grouped_top_k_output_returns_each_existing_category(category_student, category_jobs):
    grouped = group_top_k_jobs_for_student(category_student, category_jobs, top_k=2)

    assert set(grouped.keys()) == {"match", "stretch", "safe"}
    assert len(grouped["match"]) == 1
    assert len(grouped["stretch"]) == 1
    assert len(grouped["safe"]) == 1
    assert grouped["safe"][0]["category"] == "safe"
    assert grouped["match"][0]["category"] == "match"
    assert grouped["stretch"][0]["category"] == "stretch"



def test_grouped_reasons_explain_category(category_student, category_jobs):
    grouped = group_top_k_jobs_for_student(category_student, category_jobs, top_k=3)

    assert "保底岗" in grouped["safe"][0]["reason"]
    assert "匹配岗" in grouped["match"][0]["reason"]
    assert "冲刺岗" in grouped["stretch"][0]["reason"]
