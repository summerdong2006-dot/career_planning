import pytest

from app.modules.matching.matcher import rank_jobs_for_student
from app.modules.matching.schema import JobMatchProfile, MatchingWeights, StudentMatchProfile
from app.modules.matching.scorer import (
    calculate_total_score,
    score_base_requirement,
    score_growth_potential,
    score_skill_match,
    score_soft_skill_match,
)


@pytest.fixture
def student_profile() -> StudentMatchProfile:
    return StudentMatchProfile(
        student_profile_id=1,
        student_id="stu-001",
        summary="计算机专业学生，熟悉 Python、FastAPI、SQL，做过后端项目。",
        education="本科",
        career_intention="后端开发工程师",
        professional_skills=["Python", "FastAPI", "MySQL", "Git"],
        certificates=["CET-6"],
        innovation_score=72,
        learning_score=80,
        stress_score=68,
        communication_score=74,
        internship_score=62,
        professional_skill_score=78,
        completeness_score=86,
        competitiveness_score=79,
        internship_count=1,
        project_count=2,
        extracted_evidence={
            "skills": ["项目中使用 Python 和 FastAPI 开发接口服务"],
            "summary": ["熟悉 Python、FastAPI、SQL"],
            "communication": ["负责项目答辩和汇报"],
            "learning": ["自学后端框架并完成课程项目"],
            "innovation": ["参与创新创业项目"],
            "internship_ability": ["在实验室承担开发任务"],
        },
    )


@pytest.fixture
def backend_job() -> JobMatchProfile:
    return JobMatchProfile(
        job_profile_id=10,
        job_id=100,
        job_title="后端开发工程师",
        job_level="初级",
        education_requirement="本科",
        years_experience_requirement="应届/实习可投",
        must_have_skills=["Python", "SQL", "FastAPI"],
        nice_to_have_skills=["Docker"],
        certificates=[],
        soft_skills=["沟通能力", "学习能力"],
        internship_requirement="有实习经历优先",
        promotion_path=["后端开发工程师", "高级后端开发工程师", "技术负责人"],
        summary="负责 Python 后端服务开发，要求本科，有实习经历优先。",
        extracted_evidence={
            "must_have_skills": ["负责 Python 后端服务开发，熟悉 FastAPI 和 SQL"],
            "soft_skills": ["具备良好的沟通能力和学习能力"],
            "education_requirement": ["本科及以上学历"],
            "years_experience_requirement": ["应届/实习可投"],
            "summary": ["负责 Python 后端服务开发，要求本科，有实习经历优先。"],
        },
        confidence_score=90,
    )



def test_score_base_requirement(student_profile, backend_job):
    detail = score_base_requirement(student_profile, backend_job)

    assert detail.matched is True
    assert detail.score >= 80
    assert detail.unmet_items == []
    assert "基础门槛" in detail.explanation



def test_score_skill_match_supports_synonym_and_missing_skills(student_profile, backend_job):
    detail = score_skill_match(student_profile, backend_job)

    assert detail.score > 70
    assert detail.matched is True
    assert any("Python" in item for item in detail.evidence)
    assert detail.details["missing_nice_skills"] == ["Docker"]

    stronger_job = backend_job.model_copy(update={"must_have_skills": ["Python", "PostgreSQL", "Redis"]})
    stronger_detail = score_skill_match(student_profile, stronger_job)
    assert "缺少核心技能：Redis" in stronger_detail.gaps
    assert stronger_detail.matched is False



def test_score_soft_skill_match(student_profile, backend_job):
    detail = score_soft_skill_match(student_profile, backend_job)

    assert detail.score >= 70
    assert detail.details["mapped_items"][0]["mapped_ability"] == "communication"
    assert detail.gaps == []



def test_score_growth_potential(student_profile, backend_job):
    skill_detail = score_skill_match(student_profile, backend_job)
    soft_detail = score_soft_skill_match(student_profile, backend_job)
    growth_detail = score_growth_potential(student_profile, backend_job, skill_detail, soft_detail)

    assert growth_detail.score >= 70
    assert any("岗位晋升路径" in item for item in growth_detail.evidence)



def test_calculate_total_score():
    total = calculate_total_score(
        MatchingWeights(),
        {
            "base_requirement": 90,
            "skill": 80,
            "soft_skill": 70,
            "growth": 60,
        },
    )
    assert total == pytest.approx(77.5, abs=0.1)



def test_top_k_sorting_is_stable(student_profile, backend_job):
    jobs = [
        backend_job,
        backend_job.model_copy(update={"job_profile_id": 11, "job_id": 101, "job_title": "平台开发工程师", "must_have_skills": ["Python"]}),
        backend_job.model_copy(update={"job_profile_id": 12, "job_id": 102, "job_title": "数据开发工程师", "must_have_skills": ["Python", "SQL"]}),
    ]

    matches = rank_jobs_for_student(student_profile, jobs, top_k=2)
    assert len(matches) == 2
    assert matches[0].total_score >= matches[1].total_score



def test_missing_fields_are_tolerated():
    sparse_student = StudentMatchProfile(student_profile_id=2)
    sparse_job = JobMatchProfile(job_profile_id=20, job_id=200, job_title="通用岗位")

    base_detail = score_base_requirement(sparse_student, sparse_job)
    skill_detail = score_skill_match(sparse_student, sparse_job)
    soft_detail = score_soft_skill_match(sparse_student, sparse_job)
    growth_detail = score_growth_potential(sparse_student, sparse_job, skill_detail, soft_detail)

    assert base_detail.score >= 80
    assert skill_detail.score >= 55
    assert soft_detail.score >= 0
    assert growth_detail.score >= 0


