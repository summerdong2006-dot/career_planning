from __future__ import annotations

import re
from typing import Any, Mapping

from app.modules.job_profile.profile_schema import (
    EVIDENCE_FIELD_NAMES,
    JobProfileEvidence,
    JobProfilePayload,
    JobProfileSourceRecord,
    normalize_list_field,
    normalize_text_field,
)

FIELD_ALIASES = {
    "job_title": ["job_title", "title", "jobTitle", "岗位名称", "职位名称"],
    "job_level": ["job_level", "level", "jobLevel", "岗位级别"],
    "education_requirement": [
        "education_requirement",
        "education",
        "minimum_education",
        "学历要求",
    ],
    "years_experience_requirement": [
        "years_experience_requirement",
        "years_experience",
        "experience_requirement",
        "experience",
        "经验要求",
    ],
    "must_have_skills": ["must_have_skills", "required_skills", "must_skills", "核心技能"],
    "nice_to_have_skills": ["nice_to_have_skills", "preferred_skills", "bonus_skills", "加分技能"],
    "certificates": ["certificates", "certificate_requirements", "证书要求"],
    "soft_skills": ["soft_skills", "softskill", "软技能"],
    "internship_requirement": ["internship_requirement", "internship", "实习要求"],
    "industry_tags": ["industry_tags", "industries", "industry", "行业标签"],
    "promotion_path": ["promotion_path", "career_path", "晋升路径"],
    "summary": ["summary", "profile_summary", "岗位总结"],
    "extracted_evidence": ["extracted_evidence", "evidence", "证据"],
    "confidence_score": ["confidence_score", "confidence", "置信度"],
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").strip()
    return re.sub(r"\s+", " ", text)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.lower())


NORMALIZED_ALIAS_LOOKUP = {
    _normalize_key(alias): field_name
    for field_name, aliases in FIELD_ALIASES.items()
    for alias in aliases
}


def _find_field(raw_payload: Mapping[str, Any], field_name: str) -> Any:
    for key, value in raw_payload.items():
        if NORMALIZED_ALIAS_LOOKUP.get(_normalize_key(str(key))) == field_name:
            return value
    return None


def _coerce_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _coerce_evidence(value: Any) -> JobProfileEvidence:
    if not isinstance(value, Mapping):
        return JobProfileEvidence()
    evidence_payload: dict[str, list[str]] = {}
    for field_name in EVIDENCE_FIELD_NAMES:
        evidence_payload[field_name] = normalize_list_field(_find_field(value, field_name))
    return JobProfileEvidence(**evidence_payload)


def _fallback_summary(
    job_title: str,
    job_level: str,
    education_requirement: str,
    years_experience_requirement: str,
    must_have_skills: list[str],
) -> str:
    summary_parts = [job_title or "未明确"]
    if job_level != "未明确":
        summary_parts.append(job_level)
    if education_requirement != "未明确":
        summary_parts.append(f"学历要求{education_requirement}")
    if years_experience_requirement != "未明确":
        summary_parts.append(f"经验要求{years_experience_requirement}")
    if must_have_skills:
        summary_parts.append(f"核心技能：{'、'.join(must_have_skills[:5])}")
    return "，".join(summary_parts) if summary_parts else "未明确"


def normalize_profile_payload(raw_payload: Mapping[str, Any] | None, source: JobProfileSourceRecord) -> JobProfilePayload:
    payload = raw_payload or {}
    if isinstance(payload.get("profile"), Mapping):
        payload = payload["profile"]
    elif isinstance(payload.get("data"), Mapping):
        payload = payload["data"]

    job_title = normalize_text_field(_find_field(payload, "job_title"), default=source.position_name or "未明确")
    job_level = normalize_text_field(_find_field(payload, "job_level"))
    education_requirement = normalize_text_field(_find_field(payload, "education_requirement"))
    years_experience_requirement = normalize_text_field(_find_field(payload, "years_experience_requirement"))
    must_have_skills = normalize_list_field(_find_field(payload, "must_have_skills"))
    nice_to_have_skills = normalize_list_field(_find_field(payload, "nice_to_have_skills"))
    certificates = normalize_list_field(_find_field(payload, "certificates"))
    soft_skills = normalize_list_field(_find_field(payload, "soft_skills"))
    internship_requirement = normalize_text_field(_find_field(payload, "internship_requirement"))
    industry_tags = normalize_list_field(_find_field(payload, "industry_tags"))
    promotion_path = normalize_list_field(_find_field(payload, "promotion_path"))
    summary = normalize_text_field(_find_field(payload, "summary"))
    evidence = _coerce_evidence(_find_field(payload, "extracted_evidence"))
    confidence_score = _coerce_confidence(_find_field(payload, "confidence_score"))

    if summary == "未明确":
        summary = _fallback_summary(
            job_title=job_title,
            job_level=job_level,
            education_requirement=education_requirement,
            years_experience_requirement=years_experience_requirement,
            must_have_skills=must_have_skills,
        )

    normalized_payload = JobProfilePayload(
        job_title=job_title,
        job_level=job_level,
        education_requirement=education_requirement,
        years_experience_requirement=years_experience_requirement,
        must_have_skills=must_have_skills,
        nice_to_have_skills=nice_to_have_skills,
        certificates=certificates,
        soft_skills=soft_skills,
        internship_requirement=internship_requirement,
        industry_tags=industry_tags,
        promotion_path=promotion_path,
        summary=summary,
        extracted_evidence=evidence,
        confidence_score=confidence_score,
    )
    return normalized_payload
