from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.base import Base
from app.modules.job_profile.models import JobPostingProfile
from app.modules.matching.config import MATCH_PASSING_SCORE
from app.modules.matching.matcher import match_student_to_job
from app.modules.matching.models import MatchDetailRecord, MatchResultRecord
from app.modules.matching.schema import (
    JobMatchProfile,
    JobMatchResult,
    MatchDetailResponse,
    MatchingBatchRecommendResponse,
    MatchingRecommendResponse,
    MatchingWeights,
    StudentMatchProfile,
)
from app.modules.matching.utils import clamp_score, unique_keep_order
from app.modules.student_profile.models import StudentProfileRecord
from app.services.job_family import JOB_FAMILY_LABELS, classify_job_family, family_weight_for_student, is_computer_student

logger = get_logger(__name__)


async def ensure_matching_tables(session: AsyncSession) -> None:
    async with session.bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)



def _score_sort_key(result: JobMatchResult) -> tuple[float, float, float, int]:
    return (
        -result.total_score,
        -result.dimension_scores.skill,
        -result.dimension_scores.base_requirement,
        result.job_profile_id,
    )



def _extract_student_profile(record: StudentProfileRecord) -> StudentMatchProfile:
    payload = record.profile_json or {}
    ability_scores = payload.get("ability_scores") or record.ability_scores or {}
    return StudentMatchProfile(
        student_profile_id=record.id,
        student_id=record.student_id,
        major=payload.get("major") or record.major,
        summary=payload.get("summary") or record.summary,
        education=payload.get("education") or record.education,
        career_intention=payload.get("career_intention") or record.career_intention,
        professional_skills=payload.get("skills", []),
        certificates=payload.get("certificates", []),
        innovation_score=ability_scores.get("innovation", 0.0),
        learning_score=ability_scores.get("learning", 0.0),
        stress_score=ability_scores.get("stress_tolerance", 0.0),
        communication_score=ability_scores.get("communication", 0.0),
        internship_score=ability_scores.get("internship_ability", 0.0),
        professional_skill_score=ability_scores.get("professional_skills", 0.0),
        completeness_score=payload.get("completeness_score", record.completeness_score),
        competitiveness_score=payload.get("competitiveness_score", record.competitiveness_score),
        internship_count=len(payload.get("internships", [])),
        project_count=len(payload.get("projects", [])),
        extracted_evidence=payload.get("evidence") or record.extracted_evidence or {},
        missing_items=payload.get("missing_items") or record.missing_items or [],
    )



def _extract_job_profile(record: JobPostingProfile) -> JobMatchProfile:
    raw_payload = record.raw_profile_payload or {}
    growth_potential = raw_payload.get("growth_potential") or raw_payload.get("growth") or "unknown"
    return JobMatchProfile(
        job_profile_id=record.id,
        job_id=record.source_clean_id,
        job_title=record.job_title,
        job_level=record.job_level,
        education_requirement=record.education_requirement,
        years_experience_requirement=record.years_experience_requirement,
        must_have_skills=record.must_have_skills or [],
        nice_to_have_skills=record.nice_to_have_skills or [],
        certificates=record.certificates or [],
        soft_skills=record.soft_skills or [],
        internship_requirement=record.internship_requirement,
        growth_potential=growth_potential,
        promotion_path=record.promotion_path or [],
        summary=record.summary,
        industry_tags=record.industry_tags or [],
        extracted_evidence=record.extracted_evidence or {},
        confidence_score=record.confidence_score,
    )



def _apply_job_family_weighting(
    student_profile: StudentMatchProfile,
    matches: list[JobMatchResult],
) -> list[JobMatchResult]:
    is_computer_related = is_computer_student(
        major=student_profile.major,
        skills=student_profile.professional_skills,
        summary=student_profile.summary,
    )
    if not is_computer_related:
        return matches

    adjusted: list[JobMatchResult] = []
    for match in matches:
        weighted_match = match.model_copy(deep=True)
        raw_score = weighted_match.total_score
        job_family = classify_job_family(
            weighted_match.job_title,
            summary=" ".join(weighted_match.evidence),
        )
        family_weight = family_weight_for_student(
            is_computer_related=is_computer_related,
            job_family=job_family,
        )
        weighted_score = clamp_score(raw_score * family_weight)
        weighted_match.total_score = weighted_score

        base_detail = weighted_match.dimension_details.get("base_requirement")
        base_matched = base_detail.matched if base_detail is not None else weighted_match.matched
        weighted_match.matched = bool(base_matched and weighted_match.total_score >= MATCH_PASSING_SCORE)

        logger.info(
            "match_family_weight job_title=%s job_family=%s raw_score=%.2f weighted_score=%.2f",
            weighted_match.job_title,
            job_family,
            raw_score,
            weighted_score,
        )

        if family_weight < 1.0:
            family_label = JOB_FAMILY_LABELS.get(job_family, job_family)
            weighted_match.risk_flags = unique_keep_order(
                [
                    *weighted_match.risk_flags,
                    f"\u5c97\u4f4d\u65cf\u6821\u51c6: {family_label} x {family_weight:.1f}",
                ]
            )
            weighted_match.reason = (
                f"{weighted_match.reason} \u5df2\u6309\u5c97\u4f4d\u65cf\u7cfb\u6570 {family_weight:.1f} \u8c03\u6574\u3002"
            )
        adjusted.append(weighted_match)

    return adjusted

def recommend_jobs_from_profiles(
    student_profile: StudentMatchProfile,
    job_profiles: list[JobMatchProfile],
    top_k: int,
    weights: MatchingWeights | None = None,
) -> list[JobMatchResult]:
    if not job_profiles:
        return []

    raw_matches = [match_student_to_job(student_profile, job, weights=weights) for job in job_profiles]
    weighted_matches = _apply_job_family_weighting(student_profile, raw_matches)

   
    weighted_matches.sort(key=_score_sort_key)

  
    selected = []
    seen_titles = set()

    for m in weighted_matches:
        title = (m.job_title or "").strip()

        # 同岗位只保留一个
        if title in seen_titles:
            continue

        selected.append(m)
        seen_titles.add(title)

        if len(selected) >= top_k:
            break

   
    if len(selected) < top_k:
        for m in weighted_matches:
            if m not in selected:
                selected.append(m)
                if len(selected) >= top_k:
                    break

    return selected


async def _get_student_profile_or_raise(session: AsyncSession, student_profile_id: int) -> StudentProfileRecord:
    record = await session.get(StudentProfileRecord, student_profile_id)
    if record is None:
        raise AppException(
            message=f"Student profile {student_profile_id} does not exist",
            error_code="matching_student_profile_not_found",
            status_code=404,
        )
    return record


async def _get_job_profiles_or_raise(session: AsyncSession) -> list[JobPostingProfile]:
    rows = (await session.execute(select(JobPostingProfile).order_by(JobPostingProfile.id))).scalars().all()
    if not rows:
        raise AppException(
            message="No job profiles available for matching",
            error_code="matching_job_profiles_not_found",
            status_code=404,
        )
    return rows


async def _persist_matches(
    session: AsyncSession,
    student_profile_id: int,
    matches: list[JobMatchResult],
) -> list[JobMatchResult]:
    await ensure_matching_tables(session)
    persisted: list[JobMatchResult] = []
    for match in matches:
        result_record = MatchResultRecord(
            student_profile_id=student_profile_id,
            job_profile_id=match.job_profile_id,
            total_score=match.total_score,
            base_requirement_score=match.dimension_scores.base_requirement,
            skill_score=match.dimension_scores.skill,
            soft_skill_score=match.dimension_scores.soft_skill,
            growth_score=match.dimension_scores.growth,
            matched=match.matched,
            weight_config=match.weight_config.model_dump(),
            reason=match.reason,
            gap_analysis=match.gap_analysis,
            evidence=match.evidence,
            risk_flags=match.risk_flags,
        )
        session.add(result_record)
        await session.flush()
        detail_record = MatchDetailRecord(
            match_result_id=result_record.id,
            detail_payload=match.model_dump(mode="json"),
        )
        session.add(detail_record)
        await session.flush()
        match.match_id = result_record.id
        match.created_at = result_record.created_at
        persisted.append(match)
    await session.commit()
    return persisted


async def recommend_jobs_for_student(
    session: AsyncSession,
    student_profile_id: int,
    top_k: int,
    weights: MatchingWeights | None = None,
    persist: bool = True,
) -> MatchingRecommendResponse:
    student_record = await _get_student_profile_or_raise(session, student_profile_id)
    job_records = await _get_job_profiles_or_raise(session)
    student = _extract_student_profile(student_record)
    jobs = [_extract_job_profile(record) for record in job_records]
    matches = recommend_jobs_from_profiles(student, jobs, top_k=top_k, weights=weights)
    if persist and matches:
        matches = await _persist_matches(session, student_profile_id=student_profile_id, matches=matches)
    return MatchingRecommendResponse(student_profile_id=student_profile_id, top_k=top_k, matches=matches)


async def recommend_jobs_for_students_batch(
    session: AsyncSession,
    student_profile_ids: list[int],
    top_k: int,
    weights: MatchingWeights | None = None,
    persist: bool = True,
) -> MatchingBatchRecommendResponse:
    results: list[MatchingRecommendResponse] = []
    for student_profile_id in student_profile_ids:
        response = await recommend_jobs_for_student(
            session=session,
            student_profile_id=student_profile_id,
            top_k=top_k,
            weights=weights,
            persist=persist,
        )
        results.append(response)
    return MatchingBatchRecommendResponse(results=results)


async def get_match_detail(session: AsyncSession, match_id: int) -> MatchDetailResponse:
    result_record = await session.get(MatchResultRecord, match_id)
    if result_record is None:
        raise AppException(
            message=f"Match result {match_id} does not exist",
            error_code="matching_result_not_found",
            status_code=404,
        )
    detail_record = (
        await session.execute(select(MatchDetailRecord).where(MatchDetailRecord.match_result_id == match_id))
    ).scalar_one_or_none()
    if detail_record is None:
        raise AppException(
            message=f"Match detail for {match_id} does not exist",
            error_code="matching_detail_not_found",
            status_code=404,
        )
    payload: dict[str, Any] = detail_record.detail_payload or {}
    payload["match_id"] = match_id
    payload["created_at"] = result_record.created_at
    payload.setdefault("job_profile_id", result_record.job_profile_id)
    return MatchDetailResponse(
        match_id=match_id,
        student_profile_id=result_record.student_profile_id,
        result=JobMatchResult.model_validate(payload),
    )
