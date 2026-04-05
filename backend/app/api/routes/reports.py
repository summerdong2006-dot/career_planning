from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service import (
    assert_report_access,
    assert_student_profile_access,
    get_current_user,
    link_report_to_user,
)
from app.modules.reporting.schema import (
    CareerReportDetail,
    CareerReportGenerateRequest,
    CareerReportListResponse,
    CareerReportPutRequest,
    CareerReportSectionPutRequest,
    CareerReportUpdateRequest,
)
from app.modules.reporting.service import (
    export_career_report,
    generate_career_report,
    get_career_report,
    get_latest_career_report_for_student,
    list_career_reports_for_student,
    put_career_report,
    update_career_report,
    update_career_report_section,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reporting"])


@router.post("/generate", response_model=CareerReportDetail, summary="Generate a career development report")
async def generate_career_report_route(
    request: CareerReportGenerateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportDetail:
    await assert_student_profile_access(
        session=session,
        user_id=current_user.id,
        student_profile_id=request.student_profile_id,
    )
    detail = await generate_career_report(session=session, request=request)
    if detail.report_id:
        await link_report_to_user(session=session, user_id=current_user.id, report_id=detail.report_id)
    return detail


@router.get("/{report_id}", response_model=CareerReportDetail, summary="Get a career development report")
async def get_career_report_route(
    report_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportDetail:
    await assert_report_access(session=session, user_id=current_user.id, report_id=report_id)
    return await get_career_report(session=session, report_id=report_id)


@router.put(
    "/{report_id}/sections/{section_key}",
    response_model=CareerReportDetail,
    summary="Update a single report section",
)
async def update_career_report_section_route(
    report_id: int,
    section_key: str,
    request: CareerReportSectionPutRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportDetail:
    await assert_report_access(session=session, user_id=current_user.id, report_id=report_id)
    return await update_career_report_section(
        session=session,
        report_id=report_id,
        section_key=section_key,
        request=request,
    )


@router.put("/{report_id}", response_model=CareerReportDetail, summary="Merge update a career development report")
async def put_career_report_route(
    report_id: int,
    request: CareerReportPutRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportDetail:
    await assert_report_access(session=session, user_id=current_user.id, report_id=report_id)
    return await put_career_report(session=session, report_id=report_id, request=request)


@router.get(
    "/student/{student_profile_id}/latest",
    response_model=CareerReportDetail,
    summary="Get the latest report for a student profile",
)
async def get_latest_career_report_route(
    student_profile_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportDetail:
    await assert_student_profile_access(session=session, user_id=current_user.id, student_profile_id=student_profile_id)
    return await get_latest_career_report_for_student(session=session, student_profile_id=student_profile_id)


@router.get(
    "/student/{student_profile_id}",
    response_model=CareerReportListResponse,
    summary="List reports for a student profile",
)
async def list_career_reports_route(
    student_profile_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportListResponse:
    await assert_student_profile_access(session=session, user_id=current_user.id, student_profile_id=student_profile_id)
    return await list_career_reports_for_student(session=session, student_profile_id=student_profile_id)


@router.patch("/{report_id}", response_model=CareerReportDetail, summary="Update a career development report")
async def update_career_report_route(
    report_id: int,
    request: CareerReportUpdateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CareerReportDetail:
    await assert_report_access(session=session, user_id=current_user.id, report_id=report_id)
    return await update_career_report(session=session, report_id=report_id, request=request)


@router.get("/{report_id}/export", summary="Export a career development report")
async def export_career_report_route(
    report_id: int,
    format: str = Query(default="markdown"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await assert_report_access(session=session, user_id=current_user.id, report_id=report_id)
    payload = await export_career_report(session=session, report_id=report_id, export_format=format)
    headers = {"Content-Disposition": f'attachment; filename="{payload.filename}"'}
    if payload.output_path:
        headers["X-Export-Path"] = payload.output_path
    if payload.format == "json":
        return JSONResponse(
            content=payload.content,
            media_type=payload.media_type,
            headers=headers,
        )
    content = payload.content if isinstance(payload.content, bytes) else str(payload.content)
    return Response(
        content=content,
        media_type=payload.media_type,
        headers=headers,
    )
