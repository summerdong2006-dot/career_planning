from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import Base
from app.db.session import build_async_engine
from app.modules.job_profile.cleaning import CleaningIssue, clean_job_record, project_source_record
from app.modules.job_profile.data_loader import load_source_records
from app.modules.job_profile.models import JobCleaningLog, JobImportBatch, JobPostingClean, JobPostingRaw

REPO_ROOT = Path(__file__).resolve().parents[3]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_session_factory(database_url: str | None = None) -> tuple[Any, async_sessionmaker[AsyncSession]]:
    engine = build_async_engine(database_url)
    return engine, async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


def _default_batch_name(source_path: Path) -> str:
    timestamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"{source_path.stem}-{timestamp}"


def _serialize_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_export_path(batch_id: int) -> Path:
    return REPO_ROOT / "data" / "processed" / f"job_postings_batch_{batch_id}.json"


def _default_log_path(batch_id: int) -> Path:
    return REPO_ROOT / "data" / "interim" / "cleaning_v2" / f"job_cleaning_batch_{batch_id}.json"


def _log_to_model(batch_id: int, raw_id: int | None, issue: CleaningIssue) -> JobCleaningLog:
    return JobCleaningLog(
        batch_id=batch_id,
        raw_id=raw_id,
        stage=issue.stage,
        level=issue.level,
        code=issue.code,
        message=issue.message,
        details=issue.details,
    )


async def initialize_job_tables(database_url: str | None = None) -> None:
    engine = build_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


async def import_job_records(
    input_path: str,
    batch_name: str | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    source_path = Path(input_path).resolve()
    source_format, source_records = load_source_records(source_path)
    projected_records = [
        project_source_record(record=source_record, source_row_number=index)
        for index, source_record in enumerate(source_records, start=1)
    ]

    await initialize_job_tables(database_url)
    engine, session_factory = _build_session_factory(database_url)
    try:
        async with session_factory() as session:
            batch = JobImportBatch(
                batch_name=batch_name or _default_batch_name(source_path),
                source_file=str(source_path),
                source_format=source_format,
                total_records=len(projected_records),
                raw_records=len(projected_records),
                status="imported",
            )
            session.add(batch)
            await session.flush()

            raw_rows = [
                JobPostingRaw(
                    batch_id=batch.id,
                    source_row_number=record.source_row_number,
                    position_name=record.position_name,
                    work_address=record.work_address,
                    salary_range=record.salary_range,
                    company_full_name=record.company_full_name,
                    industry=record.industry,
                    company_size=record.company_size,
                    company_type=record.company_type,
                    job_code=record.job_code,
                    job_description=record.job_description,
                    company_intro=record.company_intro,
                    raw_payload=record.raw_payload,
                )
                for record in projected_records
            ]
            session.add_all(raw_rows)
            await session.commit()
            return {
                "batch_id": batch.id,
                "batch_name": batch.batch_name,
                "source_file": batch.source_file,
                "source_format": batch.source_format,
                "total_records": batch.total_records,
                "raw_records": batch.raw_records,
                "status": batch.status,
            }
    finally:
        await engine.dispose()


async def clean_job_records(
    batch_id: int,
    database_url: str | None = None,
    export_path: str | None = None,
    log_path: str | None = None,
) -> dict[str, Any]:
    await initialize_job_tables(database_url)
    engine, session_factory = _build_session_factory(database_url)
    try:
        async with session_factory() as session:
            batch = await session.get(JobImportBatch, batch_id)
            if batch is None:
                raise ValueError(f"Batch {batch_id} does not exist")

            existing_batch_clean_rows = (
                await session.execute(select(JobPostingClean.id).where(JobPostingClean.batch_id == batch_id))
            ).scalars().all()
            if existing_batch_clean_rows:
                raise ValueError(f"Batch {batch_id} has already been cleaned")

            rows = (
                await session.execute(
                    select(JobPostingRaw).where(JobPostingRaw.batch_id == batch_id).order_by(JobPostingRaw.id)
                )
            ).scalars().all()
            if not rows:
                raise ValueError(f"Batch {batch_id} does not contain raw job records")

            historical_rows = await session.execute(
                select(JobPostingClean.canonical_key, JobPostingClean.source_raw_id).where(JobPostingClean.batch_id != batch_id)
            )
            seen_keys: dict[str, int] = {canonical_key: source_raw_id for canonical_key, source_raw_id in historical_rows}
            clean_rows: list[JobPostingClean] = []
            log_rows: list[JobCleaningLog] = []
            exported_records: list[dict[str, Any]] = []
            batch.duplicate_records = 0
            batch.invalid_records = 0

            for row in rows:
                cleaned, issues = clean_job_record(
                    project_source_record(
                        record=row.raw_payload,
                        source_row_number=row.source_row_number,
                    )
                )

                for issue in issues:
                    log_rows.append(_log_to_model(batch_id=batch_id, raw_id=row.id, issue=issue))

                if cleaned.canonical_key in seen_keys:
                    row.clean_status = "duplicate"
                    batch.duplicate_records += 1
                    log_rows.append(
                        JobCleaningLog(
                            batch_id=batch_id,
                            raw_id=row.id,
                            stage="deduplicate",
                            level="info",
                            code="duplicate_record",
                            message="Record was identified as duplicate and skipped from the clean table.",
                            details={
                                "duplicate_of_raw_id": seen_keys[cleaned.canonical_key],
                                "canonical_key": cleaned.canonical_key,
                            },
                        )
                    )
                    continue

                seen_keys[cleaned.canonical_key] = row.id
                row.clean_status = "cleaned"
                clean_rows.append(
                    JobPostingClean(
                        batch_id=batch_id,
                        source_raw_id=row.id,
                        canonical_key=cleaned.canonical_key,
                        position_name=cleaned.position_name,
                        position_name_normalized=cleaned.position_name_normalized,
                        job_category=cleaned.job_category,
                        work_city=cleaned.work_city,
                        work_address=cleaned.work_address,
                        salary_range=cleaned.salary_range,
                        salary_min_monthly=cleaned.salary_min_monthly,
                        salary_max_monthly=cleaned.salary_max_monthly,
                        salary_pay_months=cleaned.salary_pay_months,
                        salary_unit=cleaned.salary_unit,
                        company_full_name=cleaned.company_full_name,
                        company_name_normalized=cleaned.company_name_normalized,
                        industry=cleaned.industry,
                        company_size=cleaned.company_size,
                        company_type=cleaned.company_type,
                        job_code=cleaned.job_code,
                        job_code_generated=cleaned.job_code_generated,
                        job_description=cleaned.job_description,
                        company_intro=cleaned.company_intro,
                        job_tags=cleaned.job_tags,
                    )
                )
                exported_records.append(cleaned.to_export_dict())

            session.add_all(clean_rows)
            session.add_all(log_rows)
            batch.unique_records = len(clean_rows)
            batch.status = "cleaned"
            batch.finished_at = _utc_now()
            await session.commit()

            export_target = Path(export_path) if export_path else _default_export_path(batch_id)
            log_target = Path(log_path) if log_path else _default_log_path(batch_id)
            _serialize_json(
                export_target,
                {
                    "batch_id": batch_id,
                    "batch_name": batch.batch_name,
                    "record_count": len(exported_records),
                    "records": exported_records,
                },
            )
            _serialize_json(
                log_target,
                {
                    "batch_id": batch_id,
                    "batch_name": batch.batch_name,
                    "summary": {
                        "total_records": batch.total_records,
                        "unique_records": batch.unique_records,
                        "duplicate_records": batch.duplicate_records,
                        "invalid_records": batch.invalid_records,
                    },
                    "logs": [
                        {
                            "raw_id": log_row.raw_id,
                            "stage": log_row.stage,
                            "level": log_row.level,
                            "code": log_row.code,
                            "message": log_row.message,
                            "details": log_row.details,
                        }
                        for log_row in log_rows
                    ],
                },
            )
            return {
                "batch_id": batch_id,
                "batch_name": batch.batch_name,
                "total_records": batch.total_records,
                "unique_records": batch.unique_records,
                "duplicate_records": batch.duplicate_records,
                "invalid_records": batch.invalid_records,
                "export_path": str(export_target),
                "log_path": str(log_target),
            }
    finally:
        await engine.dispose()

