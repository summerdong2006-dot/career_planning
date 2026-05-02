from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.modules.job_profile.models import JobCleaningLog, JobImportBatch, JobPostingClean, JobPostingRaw
from app.modules.job_profile.profile_service import extract_job_profiles_batch
from app.modules.job_profile.service import _build_session_factory, initialize_job_tables

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CLEAN_DATA_PATH = REPO_ROOT / "data" / "processed" / "jobs_master.json"
DEFAULT_LOG_DATA_PATH = REPO_ROOT / "data" / "interim" / "cleaning_v2" / "job_cleaning_master.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import cleaned job JSON into database tables and generate job profiles.")
    parser.add_argument(
        "--clean-data",
        default=str(DEFAULT_CLEAN_DATA_PATH),
        help="Path to cleaned job records JSON.",
    )
    parser.add_argument(
        "--clean-log",
        default=str(DEFAULT_LOG_DATA_PATH),
        help="Path to cleaning summary/log JSON.",
    )
    parser.add_argument("--batch-name", default=None, help="Optional batch name override.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. Defaults to configured PostgreSQL async URL.",
    )
    parser.add_argument(
        "--skip-profiles",
        action="store_true",
        help="Only import cleaned data and logs, without generating job profiles.",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _normalize_details(details: Any, raw_id_map: dict[int, int]) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in details.items():
        if key in {"duplicate_of_raw_id", "raw_id"} and isinstance(value, int):
            normalized[key] = raw_id_map.get(value, value)
        else:
            normalized[key] = value
    return normalized


async def import_cleaned_job_json(
    clean_data_path: str,
    clean_log_path: str,
    batch_name: str | None = None,
    database_url: str | None = None,
    generate_profiles: bool = True,
) -> dict[str, Any]:
    clean_path = Path(clean_data_path).resolve()
    log_path = Path(clean_log_path).resolve()
    clean_payload = _load_json(clean_path)
    log_payload = _load_json(log_path)

    records = clean_payload.get("records") or []
    logs = log_payload.get("logs") or []
    if not isinstance(records, list):
        raise ValueError("Clean data JSON field 'records' must be a list")
    if not isinstance(logs, list):
        raise ValueError("Clean log JSON field 'logs' must be a list")

    summary = log_payload.get("summary") or {}
    total_records = int(summary.get("total_records") or len(records))
    unique_records = int(summary.get("unique_records") or len(records))
    duplicate_records = int(summary.get("duplicate_records") or 0)
    invalid_records = int(summary.get("invalid_records") or 0)

    source_row_numbers = [int(item["source_row_number"]) for item in records if isinstance(item, dict) and item.get("source_row_number")]
    logged_raw_ids = [int(item["raw_id"]) for item in logs if isinstance(item, dict) and item.get("raw_id") is not None]
    max_source_row_number = max(source_row_numbers + logged_raw_ids, default=0)
    raw_row_count = max(total_records, max_source_row_number)

    await initialize_job_tables(database_url)
    engine, session_factory = _build_session_factory(database_url)
    try:
        async with session_factory() as session:
            existing_batch = (
                await session.execute(
                    select(JobImportBatch).where(
                        JobImportBatch.source_file == str(clean_path),
                        JobImportBatch.source_format == "clean_json",
                    )
                )
            ).scalar_one_or_none()

            if existing_batch is not None:
                clean_ids = (
                    await session.execute(
                        select(JobPostingClean.id).where(JobPostingClean.batch_id == existing_batch.id).order_by(JobPostingClean.id)
                    )
                ).scalars().all()
                profile_summary: dict[str, Any] = {}
                if generate_profiles and clean_ids:
                    profile_result = await extract_job_profiles_batch(
                        session=session,
                        source_clean_ids=list(clean_ids),
                        limit=len(clean_ids),
                        persist=True,
                    )
                    profile_summary = {
                        "requested_records": profile_result.requested_records,
                        "processed_records": profile_result.processed_records,
                        "persisted_records": profile_result.persisted_records,
                        "failed_records": profile_result.failed_records,
                    }
                return {
                    "batch_id": existing_batch.id,
                    "batch_name": existing_batch.batch_name,
                    "clean_records": len(clean_ids),
                    "status": existing_batch.status,
                    "source_file": str(clean_path),
                    "log_file": str(log_path),
                    "imported": False,
                    "profiles_generated": bool(generate_profiles),
                    "profile_summary": profile_summary,
                }

            batch = JobImportBatch(
                batch_name=batch_name or clean_payload.get("batch_name") or clean_path.stem,
                source_file=str(clean_path),
                source_format="clean_json",
                total_records=total_records,
                raw_records=raw_row_count,
                unique_records=unique_records,
                duplicate_records=duplicate_records,
                invalid_records=invalid_records,
                status="cleaned",
            )
            session.add(batch)
            await session.flush()

            clean_by_row_number = {
                int(record["source_row_number"]): record
                for record in records
                if isinstance(record, dict) and record.get("source_row_number") is not None
            }

            raw_rows: list[JobPostingRaw] = []
            for source_row_number in range(1, raw_row_count + 1):
                record = clean_by_row_number.get(source_row_number, {})
                raw_rows.append(
                    JobPostingRaw(
                        batch_id=batch.id,
                        source_row_number=source_row_number,
                        position_name=str(record.get("position_name") or ""),
                        work_address=str(record.get("work_address") or ""),
                        salary_range=str(record.get("salary_range") or ""),
                        company_full_name=str(record.get("company_full_name") or ""),
                        industry=str(record.get("industry") or ""),
                        company_size=str(record.get("company_size") or ""),
                        company_type=str(record.get("company_type") or ""),
                        job_code=str(record.get("job_code") or ""),
                        job_description=str(record.get("job_description") or ""),
                        company_intro=str(record.get("company_intro") or ""),
                        raw_payload=record if record else {"source_row_number": source_row_number, "placeholder": True},
                        clean_status="imported",
                    )
                )
            session.add_all(raw_rows)
            await session.flush()

            raw_id_map = {row.source_row_number: row.id for row in raw_rows}
            duplicate_source_rows = {
                int(item["raw_id"])
                for item in logs
                if isinstance(item, dict) and item.get("code") == "duplicate_record" and item.get("raw_id") is not None
            }
            for row in raw_rows:
                if row.source_row_number in clean_by_row_number:
                    row.clean_status = "cleaned"
                elif row.source_row_number in duplicate_source_rows:
                    row.clean_status = "duplicate"

            clean_rows: list[JobPostingClean] = []
            for record in records:
                source_row_number = int(record["source_row_number"])
                clean_rows.append(
                    JobPostingClean(
                        batch_id=batch.id,
                        source_raw_id=raw_id_map[source_row_number],
                        canonical_key=str(record.get("canonical_key") or ""),
                        position_name=str(record.get("position_name") or ""),
                        position_name_normalized=str(record.get("position_name_normalized") or record.get("position_name") or ""),
                        job_category=str(record.get("job_category") or ""),
                        work_city=str(record.get("work_city") or ""),
                        work_address=str(record.get("work_address") or ""),
                        salary_range=str(record.get("salary_range") or ""),
                        salary_min_monthly=record.get("salary_min_monthly"),
                        salary_max_monthly=record.get("salary_max_monthly"),
                        salary_pay_months=int(record.get("salary_pay_months") or 12),
                        salary_unit=str(record.get("salary_unit") or "monthly"),
                        company_full_name=str(record.get("company_full_name") or ""),
                        company_name_normalized=str(record.get("company_name_normalized") or record.get("company_full_name") or ""),
                        industry=str(record.get("industry") or ""),
                        company_size=str(record.get("company_size") or ""),
                        company_type=str(record.get("company_type") or ""),
                        job_code=str(record.get("job_code") or ""),
                        job_code_generated=bool(record.get("job_code_generated")),
                        job_description=str(record.get("job_description") or ""),
                        company_intro=str(record.get("company_intro") or ""),
                        job_tags=list(record.get("job_tags") or []),
                    )
                )
            session.add_all(clean_rows)

            log_rows: list[JobCleaningLog] = []
            for item in logs:
                log_rows.append(
                    JobCleaningLog(
                        batch_id=batch.id,
                        raw_id=raw_id_map.get(int(item["raw_id"])) if item.get("raw_id") is not None else None,
                        stage=str(item.get("stage") or "unknown"),
                        level=str(item.get("level") or "info"),
                        code=str(item.get("code") or "unknown"),
                        message=str(item.get("message") or ""),
                        details=_normalize_details(item.get("details"), raw_id_map),
                    )
                )
            session.add_all(log_rows)
            await session.commit()

            profile_summary: dict[str, Any] = {}
            if generate_profiles and clean_rows:
                clean_ids = [row.id for row in clean_rows]
                profile_result = await extract_job_profiles_batch(
                    session=session,
                    source_clean_ids=clean_ids,
                    limit=len(clean_ids),
                    persist=True,
                )
                profile_summary = {
                    "requested_records": profile_result.requested_records,
                    "processed_records": profile_result.processed_records,
                    "persisted_records": profile_result.persisted_records,
                    "failed_records": profile_result.failed_records,
                }

            return {
                "batch_id": batch.id,
                "batch_name": batch.batch_name,
                "total_records": total_records,
                "raw_records": raw_row_count,
                "unique_records": unique_records,
                "duplicate_records": duplicate_records,
                "invalid_records": invalid_records,
                "clean_records": len(clean_rows),
                "log_records": len(log_rows),
                "source_file": str(clean_path),
                "log_file": str(log_path),
                "imported": True,
                "profiles_generated": bool(generate_profiles),
                "profile_summary": profile_summary,
            }
    finally:
        await engine.dispose()


async def _run() -> None:
    args = build_parser().parse_args()
    summary = await import_cleaned_job_json(
        clean_data_path=args.clean_data,
        clean_log_path=args.clean_log,
        batch_name=args.batch_name,
        database_url=args.database_url,
        generate_profiles=not args.skip_profiles,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

# AI辅助生成：Qwen3-Max-Thinking, 2026-04-26