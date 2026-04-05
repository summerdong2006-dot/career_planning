from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service import assert_student_profile_access, get_current_user
from app.modules.matching.schema import (
    MatchDetailResponse,
    MatchingBatchRecommendRequest,
    MatchingBatchRecommendResponse,
    MatchingRecommendRequest,
    MatchingRecommendResponse,
)
from app.modules.matching.service import get_match_detail, recommend_jobs_for_student, recommend_jobs_for_students_batch

router = APIRouter(prefix="/api/v1/matching", tags=["matching"])


@router.post("/recommend", response_model=MatchingRecommendResponse, summary="Recommend jobs for a student profile")
async def recommend_jobs_route(
    request: MatchingRecommendRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MatchingRecommendResponse:
    await assert_student_profile_access(
        session=session,
        user_id=current_user.id,
        student_profile_id=request.student_profile_id,
    )
    return await recommend_jobs_for_student(
        session=session,
        student_profile_id=request.student_profile_id,
        top_k=request.top_k,
        weights=request.weights,
        persist=request.persist,
    )


@router.post("/recommend-batch", response_model=MatchingBatchRecommendResponse, summary="Recommend jobs in batch")
async def recommend_jobs_batch_route(
    request: MatchingBatchRecommendRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MatchingBatchRecommendResponse:
    for student_profile_id in request.student_profile_ids:
        await assert_student_profile_access(session=session, user_id=current_user.id, student_profile_id=student_profile_id)
    return await recommend_jobs_for_students_batch(
        session=session,
        student_profile_ids=request.student_profile_ids,
        top_k=request.top_k,
        weights=request.weights,
        persist=request.persist,
    )


@router.get("/{match_id}", response_model=MatchDetailResponse, summary="Get a persisted match detail")
async def get_match_detail_route(
    match_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MatchDetailResponse:
    detail = await get_match_detail(session=session, match_id=match_id)
    await assert_student_profile_access(
        session=session,
        user_id=current_user.id,
        student_profile_id=detail.student_profile_id,
    )
    return detail
