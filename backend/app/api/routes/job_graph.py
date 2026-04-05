from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.job_profile.models import JobPostingProfile
from app.services.job_graph import build_job_graph, generate_career_paths

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
    summary: str
    must_have_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    promotion_path: list[str] = Field(default_factory=list)
    career_paths: list[list[str]] = Field(default_factory=list)


class JobGraphOverviewResponse(BaseModel):
    representative_jobs: list[RepresentativeJobCard] = Field(default_factory=list)
    graph: dict[str, list[dict[str, Any]]] = Field(default_factory=lambda: {"nodes": [], "edges": []})


async def _load_representative_rows(session: AsyncSession, limit: int) -> list[JobPostingProfile]:
    rows = (await session.execute(select(JobPostingProfile).order_by(JobPostingProfile.id).limit(max(limit * 8, 40)))).scalars().all()
    selected: list[JobPostingProfile] = []
    seen_titles: set[str] = set()
    for row in rows:
        title_key = (row.job_title or "").strip().lower()
        if not title_key or title_key in seen_titles:
            continue
        if not row.must_have_skills and not row.promotion_path:
            continue
        seen_titles.add(title_key)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


@router.get("/overview", response_model=JobGraphOverviewResponse, summary="Get representative job graph overview")
async def get_job_graph_overview_route(
    limit: int = Query(default=10, ge=5, le=20),
    session: AsyncSession = Depends(get_db_session),
) -> JobGraphOverviewResponse:
    rows = await _load_representative_rows(session, limit)
    job_ids = [row.source_clean_id for row in rows]
    graph = await build_job_graph(session, job_ids=job_ids)

    representative_jobs: list[RepresentativeJobCard] = []
    for row in rows:
        paths_payload = await generate_career_paths(session, row.source_clean_id)
        representative_jobs.append(
            RepresentativeJobCard(
                job_id=row.source_clean_id,
                job_profile_id=row.id,
                job_title=row.job_title,
                job_level=row.job_level,
                summary=row.summary,
                must_have_skills=row.must_have_skills or [],
                certificates=row.certificates or [],
                promotion_path=row.promotion_path or [],
                career_paths=paths_payload.get("paths", []),
            )
        )

    return JobGraphOverviewResponse(representative_jobs=representative_jobs, graph=graph)


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
