from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.db.base import Base
from app.modules.student_profile.evidence import build_evidence
from app.modules.student_profile.models import ResumeRecord, StudentProfileItemRecord, StudentProfileRecord
from app.modules.student_profile.normalizer import normalize_profile_payload, stabilize_profile_payload
from app.modules.student_profile.parser import build_raw_profile_payload, preprocess_texts
from app.modules.student_profile.scoring import (
    attach_score_evidence,
    calculate_ability_scores,
    calculate_completeness_score,
    calculate_competitiveness_score,
    identify_missing_items,
)
from app.modules.student_profile.schema import (
    ABILITY_LABELS,
    ScoringWeights,
    StudentProfileBatchResponse,
    StudentProfileBuildResult,
    StudentProfilePayload,
    StudentProfileRecordRef,
    StudentProfileSource,
    StudentProfileUpdateRequest,
)


async def ensure_student_profile_tables(session: AsyncSession) -> None:
    async with session.bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def _next_profile_version(session: AsyncSession, student_id: str) -> int:
    result = await session.execute(
        select(func.max(StudentProfileRecord.profile_version)).where(StudentProfileRecord.student_id == student_id)
    )
    current = result.scalar_one_or_none()
    return int(current or 0) + 1



def _build_source_type(source: StudentProfileSource) -> str:
    has_resume = source.resume_text != "未明确"
    has_manual = bool(source.manual_form)
    if has_resume and has_manual:
        return "hybrid"
    if has_resume:
        return "resume"
    return "manual"


async def _persist_resume(session: AsyncSession, source: StudentProfileSource, preprocessed: dict[str, Any]) -> ResumeRecord:
    record = ResumeRecord(
        student_id=source.student_id,
        source_type=_build_source_type(source),
        resume_filename=source.resume_filename,
        resume_text=source.resume_text,
        manual_form_payload=source.manual_form,
        supplement_text=source.supplement_text,
        basic_info_payload=source.basic_info,
        normalized_text=preprocessed.get("normalized_text", ""),
        source_payload=source.model_dump(mode="json"),
    )
    session.add(record)
    await session.flush()
    return record


async def _persist_profile_items(
    session: AsyncSession,
    profile_record: StudentProfileRecord,
    profile: StudentProfilePayload,
) -> None:
    await session.execute(
        delete(StudentProfileItemRecord).where(StudentProfileItemRecord.profile_id == profile_record.id)
    )

    payload = profile.model_dump(mode="json")
    evidence = payload["evidence"]
    scalar_fields = [
        ("core", "school", "学校", payload["school"]),
        ("core", "major", "专业", payload["major"]),
        ("core", "education", "学历", payload["education"]),
        ("core", "grade", "年级", payload["grade"]),
        ("core", "career_intention", "职业意向", payload["career_intention"]),
        ("core", "summary", "摘要", payload["summary"]),
    ]
    for item_type, item_key, item_label, value in scalar_fields:
        session.add(
            StudentProfileItemRecord(
                profile_id=profile_record.id,
                student_id=profile_record.student_id,
                profile_version=profile_record.profile_version,
                item_type=item_type,
                item_key=item_key,
                item_label=item_label,
                item_value={"value": value},
                evidence={"snippets": evidence.get(item_key, [])},
            )
        )

    for field_name in ("skills", "certificates", "innovation_experiences"):
        for index, value in enumerate(payload[field_name]):
            session.add(
                StudentProfileItemRecord(
                    profile_id=profile_record.id,
                    student_id=profile_record.student_id,
                    profile_version=profile_record.profile_version,
                    item_type=field_name,
                    item_key=f"{field_name}_{index}",
                    item_label=field_name,
                    item_value={"value": value},
                    evidence={"snippets": evidence.get(field_name, [])},
                )
            )

    for field_name in ("projects", "internships", "competitions", "student_work"):
        for index, value in enumerate(payload[field_name]):
            session.add(
                StudentProfileItemRecord(
                    profile_id=profile_record.id,
                    student_id=profile_record.student_id,
                    profile_version=profile_record.profile_version,
                    item_type=field_name,
                    item_key=f"{field_name}_{index}",
                    item_label=field_name,
                    item_value=value,
                    evidence={"snippets": evidence.get(field_name, [])},
                )
            )

    for ability_field, label in ABILITY_LABELS.items():
        session.add(
            StudentProfileItemRecord(
                profile_id=profile_record.id,
                student_id=profile_record.student_id,
                profile_version=profile_record.profile_version,
                item_type="ability",
                item_key=ability_field,
                item_label=label,
                item_value={"score": payload["ability_scores"][ability_field]},
                evidence={"snippets": evidence.get(ability_field, [])},
            )
        )

    for index, value in enumerate(payload["missing_items"]):
        session.add(
            StudentProfileItemRecord(
                profile_id=profile_record.id,
                student_id=profile_record.student_id,
                profile_version=profile_record.profile_version,
                item_type="missing_item",
                item_key=f"missing_{index}",
                item_label=value["label"],
                item_value=value,
                evidence={"snippets": evidence.get("missing_items", [])},
            )
        )


async def _persist_profile(
    session: AsyncSession,
    source: StudentProfileSource,
    profile_version: int,
    resume_record: ResumeRecord,
    profile: StudentProfilePayload,
    raw_profile_payload: dict[str, Any],
) -> StudentProfileRecord:
    stable_profile = stabilize_profile_payload(profile)
    payload = stable_profile.model_dump(mode="json")
    record = StudentProfileRecord(
        student_id=source.student_id,
        resume_id=resume_record.id,
        profile_version=profile_version,
        summary=payload["summary"],
        school=payload["school"],
        major=payload["major"],
        education=payload["education"],
        grade=payload["grade"],
        career_intention=payload["career_intention"],
        resume_source=payload["resume_source"],
        completeness_score=payload["completeness_score"],
        competitiveness_score=payload["competitiveness_score"],
        ability_scores=payload["ability_scores"],
        profile_json=payload,
        extracted_evidence=payload["evidence"],
        missing_items=payload["missing_items"],
        raw_profile_payload=raw_profile_payload,
    )
    session.add(record)
    await session.flush()
    await _persist_profile_items(session, record, stable_profile)
    return record


async def build_student_profile(
    session: AsyncSession,
    source: StudentProfileSource,
    persist: bool = True,
    scoring_weights: ScoringWeights | None = None,
) -> StudentProfileBuildResult:
    weights = scoring_weights or ScoringWeights()
    preprocessed = preprocess_texts(
        resume_text=source.resume_text,
        supplement_text=source.supplement_text,
        manual_form=source.manual_form,
        basic_info=source.basic_info,
    )
    raw_profile_payload = build_raw_profile_payload(preprocessed, source.manual_form, source.basic_info)
    evidence = build_evidence(raw_profile_payload)
    ability_scores = calculate_ability_scores(raw_profile_payload, evidence)

    scoring_probe = {
        "school": raw_profile_payload["base_fields"]["school"],
        "major": raw_profile_payload["base_fields"]["major"],
        "education": raw_profile_payload["base_fields"]["education"],
        "grade": raw_profile_payload["base_fields"]["grade"],
        "skills": raw_profile_payload["skills"],
        "projects": raw_profile_payload["projects"],
        "internships": raw_profile_payload["internships"],
        "certificates": raw_profile_payload["certificates"],
        "career_intention": raw_profile_payload["career_intention"],
        "student_work": raw_profile_payload["student_work"],
        "competitions": raw_profile_payload["competitions"],
    }
    completeness_score = calculate_completeness_score(scoring_probe)
    competitiveness_score = calculate_competitiveness_score(ability_scores, weights)
    missing_items = identify_missing_items(scoring_probe, evidence)
    evidence = attach_score_evidence(
        evidence=evidence,
        ability_scores=ability_scores,
        completeness_score=completeness_score,
        competitiveness_score=competitiveness_score,
        missing_items=missing_items,
    )
    profile = stabilize_profile_payload(
        normalize_profile_payload(
            raw_profile_payload,
            {
                "ability_scores": ability_scores,
                "completeness_score": completeness_score,
                "competitiveness_score": competitiveness_score,
                "missing_items": missing_items,
                "evidence": evidence,
            },
        )
    )
    profile.evidence.summary = [profile.summary]
    profile = stabilize_profile_payload(profile)

    record_refs = StudentProfileRecordRef()
    created_at: datetime | None = None
    profile_version = 1
    if persist:
        await ensure_student_profile_tables(session)
        profile_version = await _next_profile_version(session, source.student_id)
        resume_record = await _persist_resume(session, source, preprocessed)
        profile_record = await _persist_profile(
            session=session,
            source=source,
            profile_version=profile_version,
            resume_record=resume_record,
            profile=profile,
            raw_profile_payload=raw_profile_payload,
        )
        await session.commit()
        record_refs = StudentProfileRecordRef(profile_id=profile_record.id, resume_id=resume_record.id)
        created_at = profile_record.created_at

    return StudentProfileBuildResult(
        student_id=source.student_id,
        profile_version=profile_version,
        persisted=persist,
        profile=stabilize_profile_payload(profile),
        raw_profile_payload=raw_profile_payload,
        record_refs=record_refs,
        created_at=created_at,
    )


async def batch_build_student_profiles(
    session: AsyncSession,
    items: list[StudentProfileSource],
    persist: bool = True,
    scoring_weights: ScoringWeights | None = None,
) -> StudentProfileBatchResponse:
    results: list[StudentProfileBuildResult] = []
    failures: list[dict[str, Any]] = []
    for source in items:
        try:
            result = await build_student_profile(
                session=session,
                source=source,
                persist=persist,
                scoring_weights=scoring_weights,
            )
            results.append(result)
        except Exception as exc:
            failures.append({"student_id": source.student_id, "message": str(exc)})
            await session.rollback()
    return StudentProfileBatchResponse(
        requested_records=len(items),
        processed_records=len(results),
        persisted_records=len(results) if persist else 0,
        failed_records=len(failures),
        items=results,
        failures=failures,
    )


async def get_student_profile(
    session: AsyncSession,
    student_id: str,
    version: int | None = None,
) -> StudentProfileBuildResult:
    query = select(StudentProfileRecord).where(StudentProfileRecord.student_id == student_id)
    if version is not None:
        query = query.where(StudentProfileRecord.profile_version == version)
    else:
        query = query.order_by(StudentProfileRecord.profile_version.desc()).limit(1)
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    if record is None:
        raise AppException(
            message=f"Student profile for {student_id} does not exist",
            error_code="student_profile_not_found",
            status_code=404,
        )
    profile = stabilize_profile_payload(record.profile_json)
    return StudentProfileBuildResult(
        student_id=record.student_id,
        profile_version=record.profile_version,
        persisted=True,
        profile=profile,
        raw_profile_payload=record.raw_profile_payload or {},
        record_refs=StudentProfileRecordRef(profile_id=record.id, resume_id=record.resume_id),
        created_at=record.created_at,
    )


async def _get_resume_by_id(session: AsyncSession, resume_id: int | None) -> ResumeRecord | None:
    if resume_id is None:
        return None
    return await session.get(ResumeRecord, resume_id)


async def update_student_profile(
    session: AsyncSession,
    student_id: str,
    request: StudentProfileUpdateRequest,
) -> StudentProfileBuildResult:
    latest = await get_student_profile(session, student_id)
    resume_record = await _get_resume_by_id(session, latest.record_refs.resume_id)
    if resume_record is None:
        raise AppException(
            message=f"Resume source for {student_id} does not exist",
            error_code="student_profile_resume_not_found",
            status_code=404,
        )
    source = StudentProfileSource(
        student_id=student_id,
        resume_text=request.resume_text if request.resume_text is not None else resume_record.resume_text,
        manual_form=request.manual_form if request.manual_form is not None else resume_record.manual_form_payload,
        supplement_text=request.supplement_text if request.supplement_text is not None else resume_record.supplement_text,
        basic_info=request.basic_info if request.basic_info is not None else resume_record.basic_info_payload,
        resume_filename=request.resume_filename if request.resume_filename is not None else resume_record.resume_filename,
    )
    return await build_student_profile(
        session=session,
        source=source,
        persist=request.persist,
        scoring_weights=request.scoring_weights,
    )


async def rebuild_student_profile(
    session: AsyncSession,
    student_id: str,
    version: int | None = None,
    persist: bool = True,
    scoring_weights: ScoringWeights | None = None,
) -> StudentProfileBuildResult:
    current = await get_student_profile(session, student_id, version=version)
    resume_record = await _get_resume_by_id(session, current.record_refs.resume_id)
    if resume_record is None:
        raise AppException(
            message=f"Resume source for {student_id} does not exist",
            error_code="student_profile_resume_not_found",
            status_code=404,
        )
    source = StudentProfileSource(
        student_id=student_id,
        resume_text=resume_record.resume_text,
        manual_form=resume_record.manual_form_payload,
        supplement_text=resume_record.supplement_text,
        basic_info=resume_record.basic_info_payload,
        resume_filename=resume_record.resume_filename,
    )
    return await build_student_profile(
        session=session,
        source=source,
        persist=persist,
        scoring_weights=scoring_weights,
    )


async def export_student_profile(
    session: AsyncSession,
    student_id: str,
    version: int | None = None,
) -> dict[str, Any]:
    result = await get_student_profile(session, student_id, version=version)
    return result.model_dump(mode="json")
