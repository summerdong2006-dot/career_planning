from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service import get_current_user, get_owned_student_profile, link_student_profile_to_user
from app.modules.student_profile.schema import (
    StudentProfileBatchRequest,
    StudentProfileBatchResponse,
    StudentProfileBuildRequest,
    StudentProfileBuildResult,
    StudentProfileUpdateRequest,
)
from app.modules.student_profile.service import (
    batch_build_student_profiles,
    build_student_profile,
    get_student_profile,
    rebuild_student_profile,
    update_student_profile,
)

router = APIRouter(prefix="/api/v1/student-profiles", tags=["student-profile"])


@router.post("/build", response_model=StudentProfileBuildResult, summary="Build a structured student profile")
async def build_student_profile_route(
    request: StudentProfileBuildRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StudentProfileBuildResult:
    result = await build_student_profile(
        session=session,
        source=request.source,
        persist=request.persist,
        scoring_weights=request.scoring_weights,
    )
    if result.persisted and result.record_refs.profile_id is not None:
        await link_student_profile_to_user(
            session=session,
            user_id=current_user.id,
            student_profile_id=result.record_refs.profile_id,
        )
    return result


@router.post("/batch", response_model=StudentProfileBatchResponse, summary="Build student profiles in batch")
async def batch_student_profile_route(
    request: StudentProfileBatchRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StudentProfileBatchResponse:
    result = await batch_build_student_profiles(
        session=session,
        items=request.items,
        persist=request.persist,
        scoring_weights=request.scoring_weights,
    )
    for item in result.items:
        if item.persisted and item.record_refs.profile_id is not None:
            await link_student_profile_to_user(
                session=session,
                user_id=current_user.id,
                student_profile_id=item.record_refs.profile_id,
            )
    return result


@router.get("/{student_id}", response_model=StudentProfileBuildResult, summary="Get a student profile by student ID")
async def get_student_profile_route(
    student_id: str,
    version: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StudentProfileBuildResult:
    owned_record = await get_owned_student_profile(
        session=session,
        user_id=current_user.id,
        student_id=student_id,
        version=version,
    )
    return await get_student_profile(session=session, student_id=owned_record.student_id, version=owned_record.profile_version)


@router.patch("/{student_id}", response_model=StudentProfileBuildResult, summary="Update and rebuild a student profile")
async def update_student_profile_route(
    student_id: str,
    request: StudentProfileUpdateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StudentProfileBuildResult:
    await get_owned_student_profile(session=session, user_id=current_user.id, student_id=student_id)
    result = await update_student_profile(session=session, student_id=student_id, request=request)
    if result.persisted and result.record_refs.profile_id is not None:
        await link_student_profile_to_user(
            session=session,
            user_id=current_user.id,
            student_profile_id=result.record_refs.profile_id,
        )
    return result


@router.post("/{student_id}/rebuild", response_model=StudentProfileBuildResult, summary="Rebuild a student profile")
async def rebuild_student_profile_route(
    student_id: str,
    version: int | None = Query(default=None),
    persist: bool = Query(default=True),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StudentProfileBuildResult:
    await get_owned_student_profile(session=session, user_id=current_user.id, student_id=student_id, version=version)
    result = await rebuild_student_profile(session=session, student_id=student_id, version=version, persist=persist)
    if result.persisted and result.record_refs.profile_id is not None:
        await link_student_profile_to_user(
            session=session,
            user_id=current_user.id,
            student_profile_id=result.record_refs.profile_id,
        )
    return result
