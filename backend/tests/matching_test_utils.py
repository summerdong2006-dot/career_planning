from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_profile.models import JobImportBatch, JobPostingClean, JobPostingProfile, JobPostingRaw
from app.modules.student_profile.models import StudentProfileRecord


async def seed_student_profile(
    session: AsyncSession,
    *,
    student_id: str,
    summary: str,
    education: str,
    skills: list[str],
    certificates: list[str],
    ability_scores: dict[str, float],
    completeness_score: float,
    competitiveness_score: float,
    career_intention: str = "后端开发工程师",
    missing_items: list[dict[str, Any]] | None = None,
    evidence: dict[str, list[str]] | None = None,
    internships: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
) -> StudentProfileRecord:
    payload = {
        "summary": summary,
        "education": education,
        "skills": skills,
        "certificates": certificates,
        "career_intention": career_intention,
        "ability_scores": ability_scores,
        "completeness_score": completeness_score,
        "competitiveness_score": competitiveness_score,
        "missing_items": missing_items or [],
        "evidence": evidence
        or {
            "skills": skills,
            "summary": [summary],
            "learning": ["参加课程学习"],
            "communication": ["负责团队协作与汇报"],
            "innovation": ["完成创新项目"],
            "internship_ability": ["有项目实践经验"],
        },
        "internships": internships or [],
        "projects": projects or [],
    }
    record = StudentProfileRecord(
        student_id=student_id,
        profile_version=1,
        summary=summary,
        education=education,
        career_intention=career_intention,
        completeness_score=completeness_score,
        competitiveness_score=competitiveness_score,
        ability_scores=ability_scores,
        profile_json=payload,
        extracted_evidence=payload["evidence"],
        missing_items=payload["missing_items"],
        raw_profile_payload=payload,
    )
    session.add(record)
    await session.flush()
    return record


async def seed_job_profile(
    session: AsyncSession,
    *,
    job_title: str,
    education_requirement: str,
    years_experience_requirement: str,
    must_have_skills: list[str],
    nice_to_have_skills: list[str],
    certificates: list[str],
    soft_skills: list[str],
    promotion_path: list[str],
    summary: str,
    confidence_score: float = 0.9,
    job_level: str = "初级",
    internship_requirement: str = "未明确",
    industry_tags: list[str] | None = None,
    extracted_evidence: dict[str, list[str]] | None = None,
) -> JobPostingProfile:
    batch = JobImportBatch(
        batch_name=f"batch-{job_title}",
        source_file="test.csv",
        source_format="csv",
        total_records=1,
        raw_records=1,
        unique_records=1,
        duplicate_records=0,
        invalid_records=0,
        status="completed",
    )
    session.add(batch)
    await session.flush()

    raw = JobPostingRaw(
        batch_id=batch.id,
        source_row_number=1,
        position_name=job_title,
        work_address="上海",
        salary_range="10K-20K",
        company_full_name="测试公司",
        industry="互联网",
        company_size="50-150人",
        company_type="民营公司",
        job_code=f"JOB-{batch.id}",
        job_description=summary,
        company_intro="测试公司介绍",
        raw_payload={"job_title": job_title},
    )
    session.add(raw)
    await session.flush()

    clean = JobPostingClean(
        batch_id=batch.id,
        source_raw_id=raw.id,
        canonical_key=f"canonical-{batch.id}",
        position_name=job_title,
        position_name_normalized=job_title,
        job_category=job_title,
        work_city="上海",
        work_address="上海",
        salary_range="10K-20K",
        salary_min_monthly=10000,
        salary_max_monthly=20000,
        salary_pay_months=12,
        salary_unit="monthly",
        company_full_name="测试公司",
        company_name_normalized="测试公司",
        industry="互联网",
        company_size="50-150人",
        company_type="民营公司",
        job_code=f"JOB-{batch.id}",
        job_code_generated=False,
        job_description=summary,
        company_intro="测试公司介绍",
        job_tags=must_have_skills[:2],
    )
    session.add(clean)
    await session.flush()

    profile = JobPostingProfile(
        batch_id=batch.id,
        source_clean_id=clean.id,
        job_title=job_title,
        job_level=job_level,
        education_requirement=education_requirement,
        years_experience_requirement=years_experience_requirement,
        must_have_skills=must_have_skills,
        nice_to_have_skills=nice_to_have_skills,
        certificates=certificates,
        soft_skills=soft_skills,
        internship_requirement=internship_requirement,
        industry_tags=industry_tags or ["互联网"],
        promotion_path=promotion_path,
        summary=summary,
        extracted_evidence=extracted_evidence
        or {
            "must_have_skills": [summary],
            "nice_to_have_skills": [summary],
            "soft_skills": [summary],
            "education_requirement": [summary],
            "years_experience_requirement": [summary],
            "summary": [summary],
        },
        confidence_score=confidence_score,
        extractor_name="heuristic",
        extractor_version="v1",
        raw_profile_payload={"summary": summary},
    )
    session.add(profile)
    await session.flush()
    return profile

