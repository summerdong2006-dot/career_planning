from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.job_profile.models import JobPostingClean, JobPostingProfile
from app.modules.matching.config import TEXT_DEFAULT
from app.modules.matching.schema import JobMatchProfile
from app.modules.matching.utils import normalize_text, unique_keep_order
from app.modules.student_profile.models import StudentProfileRecord
from app.services.job_family import (
    classify_job_family,
    is_blocked_family_pair,
    is_path_transition_allowed,
    is_preferred_path_family,
)
from app.services.job_similarity import coerce_job_profile, compute_job_similarity


def _title_key(value: str) -> str:
    return normalize_text(value, default="").lower()


def _mixed_id_sort_key(value: Any) -> tuple[int, str]:
    if isinstance(value, int):
        return (0, str(value).zfill(12))
    return (1, str(value))


def _job_level_rank(job: JobMatchProfile) -> int:
    corpus = f"{job.job_level} {job.job_title}".lower()
    if any(marker in corpus for marker in ("\u5b9e\u4e60", "\u6821\u62db", "\u5e94\u5c4a", "\u7ba1\u57f9")):
        return 0
    if any(marker in corpus for marker in ("\u521d\u7ea7", "junior", "\u52a9\u7406")):
        return 1
    if any(marker in corpus for marker in ("\u4e2d\u7ea7", "mid")):
        return 2
    if any(marker in corpus for marker in ("\u9ad8\u7ea7", "\u8d44\u6df1", "senior")):
        return 3
    if any(marker in corpus for marker in ("\u4e13\u5bb6", "\u67b6\u6784", "principal", "staff")):
        return 4
    if any(marker in corpus for marker in ("\u8d1f\u8d23\u4eba", "\u7ecf\u7406", "\u603b\u76d1", "leader", "\u4e3b\u7ba1", "\u7ba1\u7406\u5c97")):
        return 5
    return -1


def _job_family(profile: JobMatchProfile) -> str:
    return classify_job_family(
        profile.job_title,
        summary=profile.summary,
        skills=[*profile.must_have_skills, *profile.nice_to_have_skills],
        industry_tags=profile.industry_tags,
    )


def _title_family(title: str) -> str:
    return classify_job_family(title)


def _promotion_path_titles(profile: JobMatchProfile) -> list[str]:
    return unique_keep_order(profile.promotion_path or [])


def _is_path_title_allowed(root_family: str, title: str) -> bool:
    title_family = _title_family(title)
    if is_preferred_path_family(root_family):
        return is_preferred_path_family(title_family)
    return is_path_transition_allowed(root_family, title_family)


async def _load_job_records(
    session: AsyncSession,
    job_ids: list[int] | None = None,
) -> list[JobPostingProfile]:
    statement = select(JobPostingProfile).order_by(JobPostingProfile.source_clean_id, JobPostingProfile.id)
    if job_ids:
        statement = statement.where(JobPostingProfile.source_clean_id.in_(job_ids))
    return (await session.execute(statement)).scalars().all()


async def _load_job_profiles(
    session: AsyncSession,
    job_ids: list[int] | None = None,
) -> list[JobMatchProfile]:
    rows = await _load_job_records(session, job_ids=job_ids)
    return [coerce_job_profile(row) for row in rows]


def _related_job_pairs(
    target: JobMatchProfile,
    profiles: list[JobMatchProfile],
    *,
    top_k: int | None = None,
) -> list[tuple[JobMatchProfile, float]]:
    pairs: list[tuple[JobMatchProfile, float]] = []
    for candidate in profiles:
        if candidate.job_id == target.job_id:
            continue
        score = compute_job_similarity(target, candidate)
        pairs.append((candidate, score))

    pairs.sort(key=lambda item: (-item[1], item[0].job_id))
    if top_k is None:
        return pairs
    return pairs[:top_k]


def _build_vertical_path_titles(target: JobMatchProfile) -> list[str]:
    target_family = _job_family(target)
    promotion_titles = [title for title in _promotion_path_titles(target) if _is_path_title_allowed(target_family, title)]
    if len(promotion_titles) < 2:
        return []
    if _title_key(target.job_title) in {_title_key(title) for title in promotion_titles}:
        return promotion_titles[:3]
    return unique_keep_order([target.job_title, *promotion_titles])[:3]


def _build_horizontal_path_titles(
    target: JobMatchProfile,
    related_pairs: list[tuple[JobMatchProfile, float]],
    *,
    excluded_titles: set[str],
) -> list[str]:
    preferred: list[JobMatchProfile] = []
    fallback: list[JobMatchProfile] = []
    target_rank = _job_level_rank(target)
    target_family = _job_family(target)

    for candidate, score in related_pairs:
        if score <= 0:
            continue
        candidate_key = _title_key(candidate.job_title)
        if candidate_key in excluded_titles:
            continue

        candidate_family = _job_family(candidate)
        if is_preferred_path_family(target_family) and not is_preferred_path_family(candidate_family):
            continue
        if not is_path_transition_allowed(target_family, candidate_family):
            continue

        fallback.append(candidate)
        candidate_rank = _job_level_rank(candidate)
        if target_rank < 0 or candidate_rank < 0 or abs(candidate_rank - target_rank) <= 1:
            preferred.append(candidate)

    selected_titles: list[str] = [target.job_title]
    for group in (preferred, fallback):
        for candidate in group:
            if candidate.job_title not in selected_titles:
                selected_titles.append(candidate.job_title)
            if len(selected_titles) >= 2:
                return selected_titles
    return selected_titles if len(selected_titles) >= 2 else []


def _build_similarity_fallback_path(
    target: JobMatchProfile,
    candidate: JobMatchProfile,
) -> list[str]:
    titles = [target.job_title, candidate.job_title]
    candidate_promotion_titles = _promotion_path_titles(candidate)
    for title in candidate_promotion_titles:
        if _title_key(title) == _title_key(candidate.job_title):
            continue
        titles.append(title)
        break
    return unique_keep_order(titles)


def _dedupe_paths(paths: list[list[str]]) -> list[list[str]]:
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        normalized = tuple(unique_keep_order(path))
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(list(normalized))
    return deduped


async def find_related_jobs(session: AsyncSession, job_id: int, top_k: int = 5) -> list[dict[str, Any]]:
    profiles = await _load_job_profiles(session)
    target = next((profile for profile in profiles if profile.job_id == job_id), None)
    if target is None:
        raise AppException(
            message=f"Job profile {job_id} does not exist",
            error_code="job_graph_job_not_found",
            status_code=404,
        )

    related = _related_job_pairs(target, profiles, top_k=top_k)
    return [
        {
            "job_id": candidate.job_id,
            "job_profile_id": candidate.job_profile_id,
            "job_title": candidate.job_title,
            "job_level": candidate.job_level,
            "similarity": score,
        }
        for candidate, score in related
    ]


async def generate_career_paths(session: AsyncSession, job_id: int) -> dict[str, Any]:
    profiles = await _load_job_profiles(session)
    target = next((profile for profile in profiles if profile.job_id == job_id), None)
    if target is None:
        raise AppException(
            message=f"Job profile {job_id} does not exist",
            error_code="job_graph_job_not_found",
            status_code=404,
        )

    related_pairs = _related_job_pairs(target, profiles)
    vertical_path = _build_vertical_path_titles(target)
    horizontal_path = _build_horizontal_path_titles(
        target,
        related_pairs,
        excluded_titles={_title_key(title) for title in vertical_path[1:]},
    )

    target_family = _job_family(target)
    paths = _dedupe_paths([vertical_path, horizontal_path])
    for candidate, _score in related_pairs:
        if len(paths) >= 2:
            break
        candidate_family = _job_family(candidate)
        if is_preferred_path_family(target_family) and not is_preferred_path_family(candidate_family):
            continue
        if not is_path_transition_allowed(target_family, candidate_family):
            continue
        fallback_path = _build_similarity_fallback_path(target, candidate)
        paths = _dedupe_paths([*paths, fallback_path])

    return {
        "job_id": target.job_id,
        "job_title": target.job_title,
        "paths": paths[:2],
    }


async def build_job_graph(session: AsyncSession, job_ids: list[int]) -> dict[str, list[dict[str, Any]]]:
    profiles = await _load_job_profiles(session, job_ids=job_ids)
    if not profiles:
        return {"nodes": [], "edges": []}

    profiles.sort(key=lambda item: item.job_id)
    title_to_profile: dict[str, JobMatchProfile] = {}
    nodes_by_id: dict[Any, dict[str, Any]] = {}
    for profile in profiles:
        title_to_profile.setdefault(_title_key(profile.job_title), profile)
        nodes_by_id[profile.job_id] = {
            "job_id": profile.job_id,
            "job_profile_id": profile.job_profile_id,
            "job_title": profile.job_title,
            "job_level": profile.job_level,
        }

    def ensure_node_for_title(title: str) -> Any:
        normalized_title = normalize_text(title, default="")
        key = _title_key(normalized_title)
        matched_profile = title_to_profile.get(key)
        if matched_profile is not None:
            return matched_profile.job_id
        synthetic_id = f"promotion::{normalized_title}"
        if synthetic_id not in nodes_by_id:
            nodes_by_id[synthetic_id] = {
                "job_id": synthetic_id,
                "job_profile_id": None,
                "job_title": normalized_title,
                "job_level": TEXT_DEFAULT,
            }
        return synthetic_id

    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[Any, Any, str]] = set()

    for profile in profiles:
        profile_family = _job_family(profile)
        promotion_titles = [title for title in _promotion_path_titles(profile) if _is_path_title_allowed(profile_family, title)]
        if len(promotion_titles) < 2:
            continue
        for source_title, target_title in zip(promotion_titles, promotion_titles[1:]):
            source_job_id = ensure_node_for_title(source_title)
            target_job_id = ensure_node_for_title(target_title)
            edge_key = (source_job_id, target_job_id, "promotion")
            if source_job_id == target_job_id or edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source_job_id": source_job_id,
                    "target_job_id": target_job_id,
                    "type": "promotion",
                    "weight": 100.0,
                }
            )

    actual_node_ids = {profile.job_id for profile in profiles}
    for profile in profiles:
        source_family = _job_family(profile)
        for candidate, score in _related_job_pairs(profile, profiles, top_k=2):
            if score <= 0:
                continue
            candidate_family = _job_family(candidate)
            if is_blocked_family_pair(source_family, candidate_family):
                continue
            source_job_id, target_job_id = sorted((profile.job_id, candidate.job_id))
            if source_job_id not in actual_node_ids or target_job_id not in actual_node_ids:
                continue
            edge_key = (source_job_id, target_job_id, "transition")
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source_job_id": source_job_id,
                    "target_job_id": target_job_id,
                    "type": "transition",
                    "weight": score,
                }
            )

    nodes = sorted(nodes_by_id.values(), key=lambda item: _mixed_id_sort_key(item["job_id"]))
    edges.sort(
        key=lambda item: (
            _mixed_id_sort_key(item["source_job_id"]),
            _mixed_id_sort_key(item["target_job_id"]),
            item["type"],
        )
    )
    return {"nodes": nodes, "edges": edges}


async def search_job_profiles(session: AsyncSession, *, query: str | None = None, limit: int = 18) -> list[JobPostingProfile]:
    statement = select(JobPostingProfile).order_by(JobPostingProfile.id)
    normalized_query = (query or "").strip()
    if normalized_query:
        pattern = f"%{normalized_query}%"
        statement = statement.join(JobPostingClean, JobPostingClean.id == JobPostingProfile.source_clean_id).where(
            or_(
                JobPostingProfile.job_title.ilike(pattern),
                JobPostingProfile.summary.ilike(pattern),
                JobPostingProfile.job_level.ilike(pattern),
                JobPostingClean.position_name.ilike(pattern),
                JobPostingClean.position_name_normalized.ilike(pattern),
                JobPostingClean.company_full_name.ilike(pattern),
                JobPostingClean.industry.ilike(pattern),
                JobPostingClean.work_city.ilike(pattern),
                JobPostingClean.work_address.ilike(pattern),
            )
        )
        rows = (await session.execute(statement.limit(limit))).scalars().all()
        return [row for row in rows if row.summary or row.must_have_skills]

    rows = (await session.execute(statement.limit(max(limit * 6, 40)))).scalars().all()
    selected: list[JobPostingProfile] = []
    seen_titles: set[str] = set()
    for row in rows:
        title_key = _title_key(row.job_title)
        if not title_key or title_key in seen_titles:
            continue
        if not row.summary and not row.must_have_skills:
            continue
        seen_titles.add(title_key)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


async def get_job_profile_by_clean_id(session: AsyncSession, *, job_id: int) -> JobPostingProfile:
    row = (
        await session.execute(
            select(JobPostingProfile).where(JobPostingProfile.source_clean_id == job_id).limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppException(
            message=f"Job profile {job_id} does not exist",
            error_code="job_graph_job_not_found",
            status_code=404,
        )
    return row


async def find_job_profile_by_title(session: AsyncSession, *, job_title: str) -> JobPostingProfile:
    normalized = job_title.strip()
    if not normalized:
        raise AppException(
            message="job_title is required",
            error_code="job_graph_invalid_job_title",
            status_code=400,
        )

    exact = (
        await session.execute(
            select(JobPostingProfile).where(JobPostingProfile.job_title.ilike(normalized)).limit(1)
        )
    ).scalar_one_or_none()
    if exact is not None:
        return exact

    pattern = f"%{normalized}%"
    partial = (
        await session.execute(
            select(JobPostingProfile).where(JobPostingProfile.job_title.ilike(pattern)).order_by(JobPostingProfile.id).limit(1)
        )
    ).scalar_one_or_none()
    if partial is not None:
        return partial

    raise AppException(
        message=f'No job profile found for "{job_title}"',
        error_code="job_graph_job_not_found",
        status_code=404,
    )


async def resolve_job_profile_from_student_profile(
    session: AsyncSession,
    *,
    student_profile_id: int,
) -> tuple[StudentProfileRecord, JobPostingProfile]:
    student = await session.get(StudentProfileRecord, student_profile_id)
    if student is None:
        raise AppException(
            message=f"Student profile {student_profile_id} does not exist",
            error_code="student_profile_not_found",
            status_code=404,
        )

    candidate_texts = [
        student.career_intention,
        student.summary,
        str((student.profile_json or {}).get("career_intention", "")),
        str((student.profile_json or {}).get("target_job", "")),
    ]
    normalized_candidates = [text.strip() for text in candidate_texts if isinstance(text, str) and text.strip()]

    for candidate_text in normalized_candidates:
        try:
            return student, await find_job_profile_by_title(session, job_title=candidate_text)
        except AppException:
            continue

    jobs = await search_job_profiles(session, query=student.career_intention or student.summary, limit=1)
    if jobs:
        return student, jobs[0]

    raise AppException(
        message="No related job profile found for this student profile",
        error_code="job_graph_student_job_not_found",
        status_code=404,
    )


def build_timeline_steps(
    current_job: JobPostingProfile,
    paths: list[list[str]],
    related_titles: list[str],
) -> list[dict[str, Any]]:
    titles: list[str] = []
    for title in [current_job.job_title, *current_job.promotion_path, *related_titles]:
        normalized = normalize_text(title, default="")
        if normalized and normalized not in titles:
            titles.append(normalized)
        if len(titles) >= 5:
            break

    labels = [
        "起步阶段",
        "进阶阶段",
        "成长阶段",
        "突破阶段",
        "未来方向",
    ]

    timeline: list[dict[str, Any]] = []
    for index, title in enumerate(titles):
        path_examples = [path for path in paths if title in path]
        timeline.append(
            {
                "title": title,
                "phase": labels[min(index, len(labels) - 1)],
                "description": current_job.summary if index == 0 else f"向 {title} 发展时，建议持续积累项目证明和岗位相关技能。",
                "skills": current_job.must_have_skills[:4] if index == 0 else current_job.nice_to_have_skills[:4] or current_job.must_have_skills[:4],
                "path_examples": path_examples,
            }
        )
    return timeline


__all__ = [
    "build_job_graph",
    "build_timeline_steps",
    "find_job_profile_by_title",
    "find_related_jobs",
    "generate_career_paths",
    "get_job_profile_by_clean_id",
    "resolve_job_profile_from_student_profile",
    "search_job_profiles",
]
