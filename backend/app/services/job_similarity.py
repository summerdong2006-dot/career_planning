from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.modules.job_profile.models import JobPostingProfile
from app.modules.matching.config import TEXT_DEFAULT
from app.modules.matching.schema import JobMatchProfile
from app.modules.matching.utils import clamp_score, normalize_list, normalize_text, skill_similarity

JOB_LEVEL_PATTERNS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (0, ("实习", "校招", "应届", "管培")),
    (1, ("初级", "junior", "助理")),
    (2, ("中级", "mid")),
    (3, ("高级", "资深", "senior")),
    (4, ("专家", "架构", "principal", "staff")),
    (5, ("负责人", "经理", "总监", "leader", "主管", "管理岗")),
)

SKILL_MATCH_THRESHOLD = 0.55


def coerce_job_profile(job: JobMatchProfile | JobPostingProfile | Mapping[str, Any]) -> JobMatchProfile:
    if isinstance(job, JobMatchProfile):
        return job

    if isinstance(job, JobPostingProfile):
        raw_payload = job.raw_profile_payload or {}
        return JobMatchProfile(
            job_profile_id=job.id,
            job_id=job.source_clean_id,
            job_title=job.job_title,
            job_level=job.job_level,
            education_requirement=job.education_requirement,
            years_experience_requirement=job.years_experience_requirement,
            must_have_skills=job.must_have_skills or [],
            nice_to_have_skills=job.nice_to_have_skills or [],
            certificates=job.certificates or [],
            soft_skills=job.soft_skills or [],
            internship_requirement=job.internship_requirement,
            growth_potential=raw_payload.get("growth_potential") or raw_payload.get("growth") or TEXT_DEFAULT,
            promotion_path=job.promotion_path or [],
            summary=job.summary,
            industry_tags=job.industry_tags or [],
            extracted_evidence=job.extracted_evidence or {},
            confidence_score=job.confidence_score,
        )

    if isinstance(job, Mapping):
        payload = dict(job)
        payload.setdefault("job_profile_id", int(payload.get("id") or payload.get("job_profile_id") or 0))
        payload.setdefault(
            "job_id",
            int(payload.get("job_id") or payload.get("source_clean_id") or payload.get("id") or 0),
        )
        return JobMatchProfile.model_validate(payload)

    raise TypeError(f"Unsupported job profile type: {type(job)!r}")


def _skill_coverage(source_skills: list[str], target_skills: list[str]) -> float:
    left = normalize_list(source_skills)
    right = normalize_list(target_skills)
    if not left or not right:
        return 0.0

    total = 0.0
    for skill in left:
        best = max((skill_similarity(skill, candidate) for candidate in right), default=0.0)
        total += best if best >= SKILL_MATCH_THRESHOLD else 0.0
    return total / len(left)


def _skill_group_similarity(left_skills: list[str], right_skills: list[str]) -> float:
    if not normalize_list(left_skills) and not normalize_list(right_skills):
        return 0.0
    forward = _skill_coverage(left_skills, right_skills)
    backward = _skill_coverage(right_skills, left_skills)
    return round(((forward + backward) / 2.0) * 100.0, 2)


def _job_level_rank(job: JobMatchProfile) -> int:
    corpus = f"{normalize_text(job.job_level, default='')} {normalize_text(job.job_title, default='')}".lower()
    if not corpus.strip():
        return -1
    for rank, markers in JOB_LEVEL_PATTERNS:
        if any(marker.lower() in corpus for marker in markers):
            return rank
    return -1


def _job_level_penalty(job_a: JobMatchProfile, job_b: JobMatchProfile) -> float:
    left_rank = _job_level_rank(job_a)
    right_rank = _job_level_rank(job_b)
    if left_rank < 0 or right_rank < 0:
        return 0.0
    return min(24.0, abs(left_rank - right_rank) * 6.0)


def compute_job_similarity(
    job_a: JobMatchProfile | JobPostingProfile | Mapping[str, Any],
    job_b: JobMatchProfile | JobPostingProfile | Mapping[str, Any],
) -> float:
    left = coerce_job_profile(job_a)
    right = coerce_job_profile(job_b)

    weighted_components: list[tuple[float, float]] = []
    if left.must_have_skills or right.must_have_skills:
        weighted_components.append((0.8, _skill_group_similarity(left.must_have_skills, right.must_have_skills)))
    if left.nice_to_have_skills or right.nice_to_have_skills:
        weighted_components.append((0.2, _skill_group_similarity(left.nice_to_have_skills, right.nice_to_have_skills)))

    if not weighted_components:
        base_score = 0.0
    else:
        total_weight = sum(weight for weight, _ in weighted_components)
        base_score = sum(weight * score for weight, score in weighted_components) / total_weight

    final_score = base_score - _job_level_penalty(left, right)
    return clamp_score(round(final_score, 2))


__all__ = ["coerce_job_profile", "compute_job_similarity"]
