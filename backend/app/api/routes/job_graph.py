from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.db.session import get_db_session
from app.modules.auth.service import assert_student_profile_access, get_current_user
from app.modules.job_profile.models import JobPostingClean
from app.services.job_graph import (
    build_job_graph,
    build_timeline_steps,
    find_job_profile_by_title,
    generate_career_paths,
    get_job_profile_by_clean_id,
    resolve_job_profile_from_student_profile,
    search_job_profiles,
)

router = APIRouter(prefix="/api/v1/job-graph", tags=["job-graph"])


class JobGraphNode(BaseModel):
    job_id: int | str
    job_profile_id: int | None = None
    job_title: str
    job_level: str


class JobGraphEdge(BaseModel):
    source_job_id: int | str
    target_job_id: int | str
    type: str
    weight: float


class JobGraphCareerPaths(BaseModel):
    job_id: int
    job_title: str
    paths: list[list[str]] = Field(default_factory=list)


class RepresentativeJobCard(BaseModel):
    job_id: int
    job_profile_id: int
    job_title: str
    job_level: str
    work_city: str = ""
    work_address: str = ""
    salary_range: str = ""
    company_name: str = ""
    industry: str = ""
    company_size: str = ""
    company_type: str = ""
    summary: str
    must_have_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    promotion_path: list[str] = Field(default_factory=list)
    career_paths: list[list[str]] = Field(default_factory=list)


class JobGraphOverviewResponse(BaseModel):
    representative_jobs: list[RepresentativeJobCard] = Field(default_factory=list)
    graph: dict[str, list[dict[str, Any]]] = Field(default_factory=lambda: {"nodes": [], "edges": []})


class JobGalleryListResponse(BaseModel):
    jobs: list[RepresentativeJobCard] = Field(default_factory=list)


class JobTimelineStep(BaseModel):
    title: str
    phase: str
    description: str
    skills: list[str] = Field(default_factory=list)
    path_examples: list[list[str]] = Field(default_factory=list)


class JobPathExplorerResponse(BaseModel):
    source_mode: str
    source_label: str
    selected_job: RepresentativeJobCard
    timeline_steps: list[JobTimelineStep] = Field(default_factory=list)
    graph: dict[str, list[dict[str, Any]]] = Field(default_factory=lambda: {"nodes": [], "edges": []})


async def _build_card_payloads(session: AsyncSession, rows: list[Any], *, include_paths: bool = True) -> list[RepresentativeJobCard]:
    clean_ids = [row.source_clean_id for row in rows if row.source_clean_id is not None]
    clean_by_id: dict[int, JobPostingClean] = {}
    if clean_ids:
        clean_result = await session.execute(select(JobPostingClean).where(JobPostingClean.id.in_(clean_ids)))
        clean_by_id = {clean.id: clean for clean in clean_result.scalars().all()}

    cards: list[RepresentativeJobCard] = []
    for row in rows:
        clean = clean_by_id.get(row.source_clean_id)
        paths_payload = await generate_career_paths(session, row.source_clean_id) if include_paths else {"paths": []}
        cards.append(
            RepresentativeJobCard(
                job_id=row.source_clean_id,
                job_profile_id=row.id,
                job_title=row.job_title,
                job_level=row.job_level,
                work_city=clean.work_city if clean else "",
                work_address=clean.work_address if clean else "",
                salary_range=clean.salary_range if clean else "",
                company_name=clean.company_full_name if clean else "",
                industry=clean.industry if clean else "",
                company_size=clean.company_size if clean else "",
                company_type=clean.company_type if clean else "",
                summary=row.summary,
                must_have_skills=row.must_have_skills or [],
                certificates=row.certificates or [],
                promotion_path=row.promotion_path or [],
                career_paths=paths_payload.get("paths", []),
            )
        )
    return cards


@router.get("/overview", response_model=JobGraphOverviewResponse, summary="Get representative job graph overview")
async def get_job_graph_overview_route(
    limit: int = Query(default=10, ge=5, le=20),
    session: AsyncSession = Depends(get_db_session),
) -> JobGraphOverviewResponse:
    rows = await search_job_profiles(session, limit=limit)
    job_ids = [row.source_clean_id for row in rows]
    graph = await build_job_graph(session, job_ids=job_ids)
    return JobGraphOverviewResponse(representative_jobs=await _build_card_payloads(session, rows), graph=graph)


@router.get("/gallery", response_model=JobGalleryListResponse, summary="Search gallery jobs")
async def get_job_gallery_route(
    q: str | None = Query(default=None),
    limit: int = Query(default=18, ge=6, le=60),
    session: AsyncSession = Depends(get_db_session),
) -> JobGalleryListResponse:
    rows = await search_job_profiles(session, query=q, limit=limit)
    return JobGalleryListResponse(jobs=await _build_card_payloads(session, rows, include_paths=False))


@router.get("/path", response_model=JobPathExplorerResponse, summary="Explore one job path")
async def get_job_path_explorer_route(
    job_id: int | None = Query(default=None),
    job_title: str | None = Query(default=None),
    student_profile_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobPathExplorerResponse:
    source_mode = "job"
    source_label = ""

    if student_profile_id is not None:
        await assert_student_profile_access(session=session, user_id=current_user.id, student_profile_id=student_profile_id)
        student, selected_job = await resolve_job_profile_from_student_profile(session, student_profile_id=student_profile_id)
        source_mode = "student-profile"
        source_label = student.career_intention or student.summary or f"student_profile_id={student_profile_id}"
    elif job_title:
        selected_job = await find_job_profile_by_title(session, job_title=job_title)
        source_label = job_title
    elif job_id is not None:
        selected_job = await get_job_profile_by_clean_id(session, job_id=job_id)
        source_label = selected_job.job_title
    else:
        rows = await search_job_profiles(session, limit=1)
        if not rows:
            raise AppException(
                message="No jobs available for the gallery explorer",
                error_code="job_graph_empty_gallery",
                status_code=404,
            )
        selected_job = rows[0]
        source_label = selected_job.job_title

    selected_card = (await _build_card_payloads(session, [selected_job]))[0]
    related_titles = [title for path in selected_card.career_paths for title in path]
    graph = await build_job_graph(session, job_ids=[selected_job.source_clean_id])
    timeline_steps = [
        JobTimelineStep.model_validate(item)
        for item in build_timeline_steps(selected_job, selected_card.career_paths, related_titles)
    ]
    return JobPathExplorerResponse(
        source_mode=source_mode,
        source_label=source_label,
        selected_job=selected_card,
        timeline_steps=timeline_steps,
        graph=graph,
    )


@router.get("/{job_id}/paths", response_model=JobGraphCareerPaths, summary="Get career paths for one job")
async def get_job_graph_paths_route(
    job_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> JobGraphCareerPaths:
    payload = await generate_career_paths(session, job_id)
    return JobGraphCareerPaths(
        job_id=payload["job_id"],
        job_title=payload["job_title"],
        paths=payload.get("paths", []),
    )
