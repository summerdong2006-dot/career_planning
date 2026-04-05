from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.base import Base
from app.modules.job_profile.llm import JobProfileLLMClient, build_job_profile_llm_client
from app.modules.job_profile.models import JobPostingClean, JobPostingProfile, JobProfileExtractionLog
from app.modules.job_profile.parser import normalize_profile_payload
from app.modules.job_profile.profile_schema import (
    BatchJobProfileExtractResponse,
    JobProfileEvidence,
    JobProfileExtractionResult,
    JobProfilePayload,
    JobProfileSourceRecord,
)
from app.modules.job_profile.prompt_templates import SYSTEM_PROMPT, build_job_profile_prompt

logger = get_logger(__name__)
settings = get_settings()

SKILL_PATTERNS = [
    ("Python", ["python"]),
    ("Java", ["java"]),
    ("Go", ["golang", "go开发", "go语言"]),
    ("C++", ["c++"]),
    ("SQL", ["sql", "mysql", "postgresql", "oracle"]),
    ("FastAPI", ["fastapi"]),
    ("Django", ["django"]),
    ("Flask", ["flask"]),
    ("Spring", ["spring", "spring boot"]),
    ("React", ["react"]),
    ("Vue", ["vue"]),
    ("JavaScript", ["javascript", "js"]),
    ("TypeScript", ["typescript", "ts"]),
    ("Docker", ["docker", "云原生"]),
    ("Kubernetes", ["kubernetes", "k8s"]),
    ("Linux", ["linux"]),
    ("Git", ["git"]),
    ("Spark", ["spark"]),
    ("Hive", ["hive"]),
    ("ETL", ["etl"]),
    ("Excel", ["excel"]),
    ("Tableau", ["tableau"]),
    ("Power BI", ["power bi", "powerbi", "bi报表"]),
    ("机器学习", ["机器学习", "machine learning"]),
    ("深度学习", ["深度学习", "deep learning"]),
    ("PyTorch", ["pytorch"]),
    ("TensorFlow", ["tensorflow"]),
    ("NLP", ["nlp", "自然语言处理"]),
    ("大模型", ["大模型", "llm", "prompt"]),
    ("数据分析", ["数据分析", "数据洞察"]),
]

SOFT_SKILL_PATTERNS = [
    ("沟通能力", ["沟通能力", "沟通协调", "表达能力"]),
    ("团队协作", ["团队协作", "团队合作", "跨团队"]),
    ("责任心", ["责任心", "认真负责"]),
    ("学习能力", ["学习能力", "快速学习", "学习意愿"]),
    ("抗压能力", ["抗压能力", "承压能力"]),
    ("执行力", ["执行力"]),
    ("逻辑思维", ["逻辑思维", "逻辑能力"]),
    ("自驱力", ["自驱", "主动性"]),
]

CERTIFICATE_PATTERNS = [
    ("PMP", ["pmp"]),
    ("软考", ["软考"]),
    ("教师资格证", ["教师资格证"]),
    ("CPA", ["cpa"]),
    ("CFA", ["cfa"]),
    ("证券从业资格", ["证券从业"]),
    ("CET-4", ["cet-4", "英语四级", "四级"]),
    ("CET-6", ["cet-6", "英语六级", "六级"]),
]

MUST_HAVE_MARKERS = ["任职要求", "岗位要求", "熟悉", "掌握", "精通", "具备", "负责", "能够", "要求"]
PREFERRED_MARKERS = ["优先", "加分", "优先考虑", "优先录用"]
INTERN_MARKERS = ["实习", "每周", "到岗", "转正", "应届", "校招"]


async def ensure_job_profile_tables(session: AsyncSession) -> None:
    async with session.bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").strip()
    return re.sub(r"\s+", " ", text)


def _unique(items: Iterable[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        text = _clean_text(item)
        if text and text not in output:
            output.append(text)
    return output


def _split_sentences(*texts: str) -> list[str]:
    sentences: list[str] = []
    for text in texts:
        normalized = _clean_text(text)
        if not normalized:
            continue
        for part in re.split(r"[\n。；;!?！？，,|]+", normalized):
            snippet = _clean_text(part)
            if snippet:
                sentences.append(snippet)
    return sentences


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _extract_terms(
    sentences: list[str],
    patterns: list[tuple[str, list[str]]],
    required_markers: list[str] | None = None,
    excluded_markers: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    terms: list[str] = []
    evidence: list[str] = []
    for sentence in sentences:
        if required_markers and not _contains_any(sentence, required_markers):
            continue
        if excluded_markers and _contains_any(sentence, excluded_markers):
            continue
        lowered = sentence.lower()
        for canonical, aliases in patterns:
            if any(alias.lower() in lowered for alias in aliases):
                if canonical not in terms:
                    terms.append(canonical)
                if sentence not in evidence:
                    evidence.append(sentence)
    return terms, evidence[:3]


def _extract_job_level(position_name: str, job_description: str) -> tuple[str, list[str]]:
    corpus = f"{position_name} {job_description}"
    mapping = [
        ("实习/校招", ["实习", "校招", "应届", "管培"]),
        ("管理岗", ["负责人", "经理", "总监", "主管", "leader"]),
        ("专家/架构", ["专家", "架构师", "principal"]),
        ("高级", ["高级", "资深", "senior"]),
        ("初级", ["初级", "助理", "junior"]),
    ]
    sentences = _split_sentences(position_name, job_description)
    lowered = corpus.lower()
    for level, keywords in mapping:
        if any(keyword.lower() in lowered for keyword in keywords):
            evidence = [sentence for sentence in sentences if any(keyword.lower() in sentence.lower() for keyword in keywords)]
            return level, evidence[:3]
    return "未明确", []


def _extract_education(job_description: str) -> tuple[str, list[str]]:
    patterns = [
        ("博士", r"博士"),
        ("硕士", r"硕士"),
        ("本科", r"本科|学士"),
        ("大专", r"大专"),
        ("学历不限", r"学历不限|不限学历"),
    ]
    for value, pattern in patterns:
        match = re.search(pattern, job_description, re.IGNORECASE)
        if match:
            sentences = [sentence for sentence in _split_sentences(job_description) if match.group(0) in sentence]
            return value, sentences[:3]
    return "未明确", []


def _extract_years_experience(job_description: str, position_name: str) -> tuple[str, list[str]]:
    if re.search(r"应届|校招|实习", f"{position_name} {job_description}"):
        sentences = [sentence for sentence in _split_sentences(position_name, job_description) if re.search(r"应届|校招|实习", sentence)]
        return "应届/实习可投", sentences[:3]

    match = re.search(r"(\d+\s*[-~至到]\s*\d+\s*年|\d+\s*年(?:以上|及以上)?|经验不限)", job_description)
    if match:
        sentences = [sentence for sentence in _split_sentences(job_description) if match.group(0) in sentence]
        return match.group(0).replace(" ", ""), sentences[:3]
    return "未明确", []


def _extract_internship_requirement(job_description: str, position_name: str) -> tuple[str, list[str]]:
    sentences = [sentence for sentence in _split_sentences(position_name, job_description) if _contains_any(sentence, INTERN_MARKERS)]
    if not sentences:
        return "未明确", []
    if any("每周" in sentence or "到岗" in sentence for sentence in sentences):
        return sentences[0], sentences[:3]
    if any("转正" in sentence for sentence in sentences):
        return "实习，表现优秀可转正", sentences[:3]
    if any("应届" in sentence or "校招" in sentence for sentence in sentences):
        return "面向应届/校招生", sentences[:3]
    return "需要实习经历或可接受实习", sentences[:3]


def _extract_industry_tags(source: JobProfileSourceRecord) -> tuple[list[str], list[str]]:
    raw_tags = re.split(r"[,，/、|]+", _clean_text(source.industry))
    tags = [tag for tag in raw_tags if tag]
    if source.job_category and source.job_category not in tags:
        tags.append(source.job_category)
    evidence = [_clean_text(source.industry)] if _clean_text(source.industry) else []
    return _unique(tags), evidence[:3]


def _infer_promotion_path(job_title: str, job_level: str) -> list[str]:
    title = _clean_text(job_title) or "岗位"
    if job_level == "实习/校招":
        return [title, f"正式{title}", f"高级{title}"]
    if job_level == "初级":
        return [title, f"中级{title}", f"高级{title}"]
    if job_level == "高级":
        return [title, "技术负责人", "技术专家"]
    if job_level == "管理岗":
        return [title, "部门负责人", "业务负责人"]
    return [title, f"高级{title}", "技术负责人"]


def _build_summary(profile: Mapping[str, Any]) -> str:
    must_skills = "、".join(profile["must_have_skills"][:5]) if profile["must_have_skills"] else "未明确"
    return (
        f"{profile['job_title']}，岗位级别{profile['job_level']}，"
        f"学历要求{profile['education_requirement']}，经验要求{profile['years_experience_requirement']}，"
        f"核心技能包括{must_skills}。"
    )


def _calculate_confidence(profile: Mapping[str, Any], evidence: Mapping[str, list[str]]) -> float:
    scalar_fields = [
        "job_level",
        "education_requirement",
        "years_experience_requirement",
        "internship_requirement",
        "summary",
    ]
    list_fields = [
        "must_have_skills",
        "nice_to_have_skills",
        "certificates",
        "soft_skills",
        "industry_tags",
        "promotion_path",
    ]
    score = 0.25
    score += 0.08 * sum(1 for field in scalar_fields if profile.get(field) not in {"", "未明确"})
    score += 0.05 * sum(1 for field in list_fields if profile.get(field))
    score += 0.03 * sum(1 for field, snippets in evidence.items() if snippets)
    return max(0.15, min(0.95, round(score, 2)))


def build_source_record_from_clean(clean_row: JobPostingClean) -> JobProfileSourceRecord:
    return JobProfileSourceRecord(
        source_clean_id=clean_row.id,
        batch_id=clean_row.batch_id,
        canonical_key=clean_row.canonical_key,
        position_name=clean_row.position_name,
        position_name_normalized=clean_row.position_name_normalized,
        job_category=clean_row.job_category,
        work_city=clean_row.work_city,
        salary_range=clean_row.salary_range,
        company_full_name=clean_row.company_full_name,
        industry=clean_row.industry,
        job_description=clean_row.job_description,
        company_intro=clean_row.company_intro,
        job_tags=clean_row.job_tags or [],
    )


def _build_extraction_result(
    source: JobProfileSourceRecord,
    profile: JobProfilePayload,
    raw_payload: dict[str, Any],
    extractor_name: str,
    persisted: bool,
) -> JobProfileExtractionResult:
    return JobProfileExtractionResult(
        source_clean_id=source.source_clean_id,
        batch_id=source.batch_id,
        extractor_name=extractor_name,
        extractor_version=settings.job_profile_extractor_version,
        persisted=persisted,
        profile=JobProfilePayload.model_validate(profile.model_dump()),
        raw_profile_payload=raw_payload if isinstance(raw_payload, dict) else {},
    )


def build_heuristic_profile(source: JobProfileSourceRecord) -> dict[str, Any]:
    job_description = _clean_text(source.job_description)
    company_intro = _clean_text(source.company_intro)
    all_sentences = _split_sentences(source.position_name, job_description, company_intro)

    must_have_skills, must_evidence = _extract_terms(
        all_sentences,
        SKILL_PATTERNS,
        required_markers=MUST_HAVE_MARKERS,
        excluded_markers=PREFERRED_MARKERS,
    )
    fallback_skills, fallback_skill_evidence = _extract_terms(all_sentences, SKILL_PATTERNS)
    if not must_have_skills:
        must_have_skills = fallback_skills[:6]
        must_evidence = fallback_skill_evidence[:3]
    for tag in source.job_tags:
        if tag not in must_have_skills and tag in {name for name, _ in SKILL_PATTERNS}:
            must_have_skills.append(tag)

    nice_to_have_skills, nice_evidence = _extract_terms(
        all_sentences,
        SKILL_PATTERNS,
        required_markers=PREFERRED_MARKERS,
    )
    certificates, certificate_evidence = _extract_terms(all_sentences, CERTIFICATE_PATTERNS)
    soft_skills, soft_evidence = _extract_terms(all_sentences, SOFT_SKILL_PATTERNS)
    job_level, job_level_evidence = _extract_job_level(source.position_name, job_description)
    education_requirement, education_evidence = _extract_education(job_description)
    years_experience_requirement, experience_evidence = _extract_years_experience(job_description, source.position_name)
    internship_requirement, internship_evidence = _extract_internship_requirement(job_description, source.position_name)
    industry_tags, industry_evidence = _extract_industry_tags(source)
    promotion_path = _infer_promotion_path(source.position_name, job_level)

    evidence = JobProfileEvidence(
        job_title=[source.position_name],
        job_level=job_level_evidence,
        education_requirement=education_evidence,
        years_experience_requirement=experience_evidence,
        must_have_skills=must_evidence,
        nice_to_have_skills=nice_evidence,
        certificates=certificate_evidence,
        soft_skills=soft_evidence,
        internship_requirement=internship_evidence,
        industry_tags=industry_evidence,
        promotion_path=[],
        summary=[],
    )

    profile = {
        "job_title": source.position_name,
        "job_level": job_level,
        "education_requirement": education_requirement,
        "years_experience_requirement": years_experience_requirement,
        "must_have_skills": _unique(must_have_skills[:8]),
        "nice_to_have_skills": _unique(nice_to_have_skills[:6]),
        "certificates": certificates,
        "soft_skills": soft_skills,
        "internship_requirement": internship_requirement,
        "industry_tags": industry_tags,
        "promotion_path": promotion_path,
    }
    profile["summary"] = _build_summary(profile)
    evidence.summary = [profile["summary"]]
    profile["extracted_evidence"] = evidence.model_dump()
    profile["confidence_score"] = _calculate_confidence(profile, evidence.model_dump())
    return profile


async def extract_job_profile_from_source(
    source: JobProfileSourceRecord,
    llm_client: JobProfileLLMClient | None = None,
) -> tuple[JobProfilePayload, dict[str, Any], str]:
    client = llm_client or build_job_profile_llm_client()
    prompt = build_job_profile_prompt(source)
    raw_payload = await client.extract(SYSTEM_PROMPT, prompt)
    extractor_name = getattr(client, "provider_name", "heuristic")

    if raw_payload is None:
        raw_payload = build_heuristic_profile(source)
        extractor_name = "heuristic"

    normalized = normalize_profile_payload(raw_payload, source)
    if normalized.summary == "未明确":
        normalized.summary = _build_summary(normalized.model_dump())
    return JobProfilePayload.model_validate(normalized.model_dump()), raw_payload, extractor_name


async def _fetch_clean_row(session: AsyncSession, source_clean_id: int) -> JobPostingClean:
    clean_row = await session.get(JobPostingClean, source_clean_id)
    if clean_row is None:
        raise AppException(
            message=f"Clean job record {source_clean_id} does not exist",
            error_code="job_profile_source_not_found",
            status_code=404,
        )
    return clean_row


async def _write_profile_log(
    session: AsyncSession,
    batch_id: int | None,
    clean_id: int | None,
    level: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        JobProfileExtractionLog(
            batch_id=batch_id,
            clean_id=clean_id,
            level=level,
            code=code,
            message=message,
            details=details or {},
        )
    )


async def _persist_profile(
    session: AsyncSession,
    source: JobProfileSourceRecord,
    profile: JobProfilePayload,
    raw_payload: dict[str, Any],
    extractor_name: str,
) -> None:
    if source.source_clean_id is None or source.batch_id is None:
        return

    existing = await session.execute(
        select(JobPostingProfile).where(JobPostingProfile.source_clean_id == source.source_clean_id)
    )
    instance = existing.scalar_one_or_none()
    profile_data = profile.model_dump()
    if instance is None:
        instance = JobPostingProfile(
            batch_id=source.batch_id,
            source_clean_id=source.source_clean_id,
        )
        session.add(instance)

    instance.batch_id = source.batch_id
    instance.job_title = profile_data["job_title"]
    instance.job_level = profile_data["job_level"]
    instance.education_requirement = profile_data["education_requirement"]
    instance.years_experience_requirement = profile_data["years_experience_requirement"]
    instance.must_have_skills = profile_data["must_have_skills"]
    instance.nice_to_have_skills = profile_data["nice_to_have_skills"]
    instance.certificates = profile_data["certificates"]
    instance.soft_skills = profile_data["soft_skills"]
    instance.internship_requirement = profile_data["internship_requirement"]
    instance.industry_tags = profile_data["industry_tags"]
    instance.promotion_path = profile_data["promotion_path"]
    instance.summary = profile_data["summary"]
    instance.extracted_evidence = profile_data["extracted_evidence"]
    instance.confidence_score = profile_data["confidence_score"]
    instance.extractor_name = extractor_name
    instance.extractor_version = settings.job_profile_extractor_version
    instance.raw_profile_payload = raw_payload


async def extract_single_job_profile(
    session: AsyncSession,
    source_clean_id: int | None = None,
    job_data: JobProfileSourceRecord | None = None,
    persist: bool = True,
    llm_client: JobProfileLLMClient | None = None,
) -> JobProfileExtractionResult:
    source = job_data
    if source is None and source_clean_id is not None:
        clean_row = await _fetch_clean_row(session, source_clean_id)
        source = build_source_record_from_clean(clean_row)
    if source is None:
        raise AppException(
            message="Either source_clean_id or job_data must be provided",
            error_code="job_profile_invalid_input",
            status_code=400,
        )

    profile, raw_payload, extractor_name = await extract_job_profile_from_source(source, llm_client=llm_client)
    persisted = False
    if persist and source.source_clean_id is not None and source.batch_id is not None:
        await ensure_job_profile_tables(session)
        await _persist_profile(session, source, profile, raw_payload, extractor_name)
        await session.commit()
        persisted = True
    elif persist and source.source_clean_id is None:
        logger.warning("Skip persistence for ad-hoc job profile extraction because source_clean_id is missing")

    return _build_extraction_result(
        source=source,
        profile=profile,
        raw_payload=raw_payload,
        extractor_name=extractor_name,
        persisted=persisted,
    )


async def extract_job_profiles_batch(
    session: AsyncSession,
    batch_id: int | None = None,
    source_clean_ids: list[int] | None = None,
    limit: int | None = None,
    persist: bool = True,
    llm_client: JobProfileLLMClient | None = None,
) -> BatchJobProfileExtractResponse:
    safe_limit = limit or 999999
    if persist:
        await ensure_job_profile_tables(session)

    ids = source_clean_ids or []
    failures: list[dict[str, Any]] = []
    items: list[JobProfileExtractionResult] = []

    if batch_id is not None:
        rows = (
            await session.execute(
                select(JobPostingClean)
                .where(JobPostingClean.batch_id == batch_id)
                .order_by(JobPostingClean.id)
                .limit(safe_limit)
            )
        ).scalars().all()
    elif ids:
        rows = (
            await session.execute(
                select(JobPostingClean)
                .where(JobPostingClean.id.in_(ids[:safe_limit]))
                .order_by(JobPostingClean.id)
            )
        ).scalars().all()
    else:
        raise AppException(
            message="Either batch_id or source_clean_ids must be provided",
            error_code="job_profile_invalid_input",
            status_code=400,
        )

    for row in rows:
        source = build_source_record_from_clean(row)
        try:
            profile, raw_payload, extractor_name = await extract_job_profile_from_source(source, llm_client=llm_client)
            if persist:
                await _persist_profile(session, source, profile, raw_payload, extractor_name)
            items.append(
                _build_extraction_result(
                    source=source,
                    profile=profile,
                    raw_payload=raw_payload,
                    extractor_name=extractor_name,
                    persisted=bool(persist),
                )
            )
        except Exception as exc:
            logger.exception("Job profile extraction failed for clean_id=%s", row.id, exc_info=exc)
            failures.append(
                {
                    "source_clean_id": row.id,
                    "message": str(exc),
                }
            )
            await _write_profile_log(
                session=session,
                batch_id=row.batch_id,
                clean_id=row.id,
                level="error",
                code="extract_failed",
                message="Job profile extraction failed for the record.",
                details={"error": str(exc)},
            )

    if persist:
        await session.commit()

    return BatchJobProfileExtractResponse(
        batch_id=batch_id,
        requested_records=len(rows),
        processed_records=len(items),
        persisted_records=len(items) if persist else 0,
        failed_records=len(failures),
        limit=safe_limit,
        items=items,
        failures=failures,
    )
