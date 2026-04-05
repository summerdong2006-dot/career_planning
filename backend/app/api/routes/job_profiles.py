from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.job_profile.profile_schema import (
    BatchJobProfileExtractRequest,
    BatchJobProfileExtractResponse,
    JobProfileExtractionResult,
    SingleJobProfileExtractRequest,
)
from app.modules.job_profile.profile_service import extract_job_profiles_batch, extract_single_job_profile

router = APIRouter(prefix="/api/v1/job-profiles", tags=["job-profile"])


@router.post(
    "/extract",
    response_model=JobProfileExtractionResult,
    summary="Extract a single structured job profile",
)
async def extract_single_job_profile_route(
    request: SingleJobProfileExtractRequest,
    session: AsyncSession = Depends(get_db_session),
) -> JobProfileExtractionResult:
    return await extract_single_job_profile(
        session=session,
        source_clean_id=request.source_clean_id,
        job_data=request.job_data,
        persist=request.persist,
    )


@router.post(
    "/extract/batch",
    response_model=BatchJobProfileExtractResponse,
    summary="Extract structured job profiles for a limited batch",
)
async def extract_job_profiles_batch_route(
    request: BatchJobProfileExtractRequest,
    session: AsyncSession = Depends(get_db_session),
) -> BatchJobProfileExtractResponse:
    return await extract_job_profiles_batch(
        session=session,
        batch_id=request.batch_id,
        source_clean_ids=request.source_clean_ids,
        limit=request.limit,
        persist=request.persist,
    )
