from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service import (
    assert_resume_access,
    assert_student_profile_access,
    get_current_user,
    link_resume_to_user,
)
from app.modules.resumes.schema import ResumeDetail, ResumeGenerateRequest, ResumeUpdateRequest
from app.modules.resumes.service import export_resume, generate_resume, get_resume, update_resume

router = APIRouter(prefix="/api/v1/resumes", tags=["resumes"])


@router.post("/generate", response_model=ResumeDetail, summary="Generate a job-tailored technical resume")
async def generate_resume_route(
    request: ResumeGenerateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeDetail:
    await assert_student_profile_access(
        session=session,
        user_id=current_user.id,
        student_profile_id=request.student_profile_id,
    )
    detail = await generate_resume(session=session, request=request)
    if detail.resume_id:
        await link_resume_to_user(session=session, user_id=current_user.id, resume_id=detail.resume_id)
    return detail


@router.get("/{resume_id}", response_model=ResumeDetail, summary="Get a generated resume")
async def get_resume_route(
    resume_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeDetail:
    await assert_resume_access(session=session, user_id=current_user.id, resume_id=resume_id)
    return await get_resume(session=session, resume_id=resume_id)


@router.put("/{resume_id}", response_model=ResumeDetail, summary="Update a generated resume")
async def update_resume_route(
    resume_id: int,
    request: ResumeUpdateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeDetail:
    await assert_resume_access(session=session, user_id=current_user.id, resume_id=resume_id)
    return await update_resume(session=session, resume_id=resume_id, request=request)


@router.get("/{resume_id}/export", summary="Export a generated resume")
async def export_resume_route(
    resume_id: int,
    format: str = Query(default="markdown"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await assert_resume_access(session=session, user_id=current_user.id, resume_id=resume_id)
    payload = await export_resume(session=session, resume_id=resume_id, export_format=format)
    headers = {"Content-Disposition": f'attachment; filename="{payload.filename}"'}
    if payload.format == "json":
        return JSONResponse(content=payload.content, media_type=payload.media_type, headers=headers)
    return Response(content=str(payload.content), media_type=payload.media_type, headers=headers)
