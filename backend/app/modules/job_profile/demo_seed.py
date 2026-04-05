from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.job_profile.import_cleaned_jobs import import_cleaned_job_json
from app.modules.job_profile.models import JobPostingClean, JobPostingProfile
from app.modules.job_profile.profile_service import extract_job_profiles_batch
from app.modules.job_profile.service import clean_job_records, import_job_records, initialize_job_tables

logger = get_logger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CLEAN_DATA_PATH = REPO_ROOT / "data" / "processed" / "jobs_master.json"
DEFAULT_CLEAN_LOG_PATH = REPO_ROOT / "data" / "interim" / "cleaning_v2" / "job_cleaning_master.json"


async def seed_demo_job_profiles_if_needed(
    session: AsyncSession,
    *,
    seed_path: str,
) -> None:
    await initialize_job_tables()

    if DEFAULT_CLEAN_DATA_PATH.exists() and DEFAULT_CLEAN_LOG_PATH.exists():
        summary = await import_cleaned_job_json(
            clean_data_path=str(DEFAULT_CLEAN_DATA_PATH),
            clean_log_path=str(DEFAULT_CLEAN_LOG_PATH),
            batch_name="official-jobs",
            generate_profiles=False,
        )
        logger.info(
            "Loaded cleaned master job data into database: batch_id=%s clean_records=%s imported=%s",
            summary.get("batch_id"),
            summary.get("clean_records"),
            summary.get("imported"),
        )
        return

    existing_profile_ids = (
        await session.execute(select(JobPostingProfile.id).limit(1))
    ).scalars().first()
    if existing_profile_ids is not None:
        logger.info("Skip demo job seeding because job profiles already exist")
        return

    seed_file = Path(seed_path)
    if not seed_file.exists():
        logger.warning("Skip demo job seeding because seed file does not exist: %s", seed_file)
        return

    clean_rows_without_profiles = (
        await session.execute(
            select(JobPostingClean.id)
            .outerjoin(JobPostingProfile, JobPostingProfile.source_clean_id == JobPostingClean.id)
            .where(JobPostingProfile.id.is_(None))
            .order_by(JobPostingClean.id)
        )
    ).scalars().all()

    if clean_rows_without_profiles:
        await extract_job_profiles_batch(
            session=session,
            source_clean_ids=clean_rows_without_profiles,
            limit=len(clean_rows_without_profiles),
            persist=True,
        )
        logger.info("Seeded demo job profiles from %s existing cleaned rows", len(clean_rows_without_profiles))
        return

    logger.info("Importing demo job seed from %s", seed_file)
    import_summary = await import_job_records(
        input_path=str(seed_file),
        batch_name="demo-job-seed",
    )
    batch_id = int(import_summary["batch_id"])

    clean_summary = await clean_job_records(
        batch_id=batch_id,
        export_path=None,
        log_path=None,
    )

    logger.info(
        "Demo job seed imported and cleaned: batch_id=%s unique_records=%s",
        batch_id,
        clean_summary["unique_records"],
    )

    await extract_job_profiles_batch(
        session=session,
        batch_id=batch_id,
        limit=max(int(clean_summary["unique_records"]), 1),
        persist=True,
    )
    logger.info("Demo job profiles extracted for batch_id=%s", batch_id)
