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
    career_intention: str = "\u540e\u7aef\u5f00\u53d1\u5de5\u7a0b\u5e08",
    major: str = "\u672a\u660e\u786e",
    missing_items: list[dict[str, Any]] | None = None,
    evidence: dict[str, list[str]] | None = None,
    internships: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
) -> StudentProfileRecord:
    payload = {
        "summary": summary,
        "major": major,
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
            "learning": ["\u53c2\u52a0\u8bfe\u7a0b\u5b66\u4e60"],
            "communication": ["\u8d1f\u8d23\u56e2\u961f\u534f\u4f5c\u4e0e\u6c47\u62a5"],
            "innovation": ["\u5b8c\u6210\u521b\u65b0\u9879\u76ee"],
            "internship_ability": ["\u6709\u9879\u76ee\u5b9e\u8df5\u7ecf\u9a8c"],
        },
        "internships": internships or [],
        "projects": projects or [],
    }
    record = StudentProfileRecord(
        student_id=student_id,
        profile_version=1,
        summary=summary,
        major=major,
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
    job_level: str = "\u521d\u7ea7",
    internship_requirement: str = "\u672a\u660e\u786e",
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
        work_address="\u4e0a\u6d77",
        salary_range="10K-20K",
        company_full_name="\u6d4b\u8bd5\u516c\u53f8",
        industry="\u4e92\u8054\u7f51",
        company_size="50-150\u4eba",
        company_type="\u6c11\u8425\u516c\u53f8",
        job_code=f"JOB-{batch.id}",
        job_description=summary,
        company_intro="\u6d4b\u8bd5\u516c\u53f8\u4ecb\u7ecd",
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
        work_city="\u4e0a\u6d77",
        work_address="\u4e0a\u6d77",
        salary_range="10K-20K",
        salary_min_monthly=10000,
        salary_max_monthly=20000,
        salary_pay_months=12,
        salary_unit="monthly",
        company_full_name="\u6d4b\u8bd5\u516c\u53f8",
        company_name_normalized="\u6d4b\u8bd5\u516c\u53f8",
        industry="\u4e92\u8054\u7f51",
        company_size="50-150\u4eba",
        company_type="\u6c11\u8425\u516c\u53f8",
        job_code=f"JOB-{batch.id}",
        job_code_generated=False,
        job_description=summary,
        company_intro="\u6d4b\u8bd5\u516c\u53f8\u4ecb\u7ecd",
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
        industry_tags=industry_tags or ["\u4e92\u8054\u7f51"],
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