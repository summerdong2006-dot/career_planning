from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.db.base import Base
from app.modules.matching.utils import normalize_list, normalize_text, unique_keep_order
from app.modules.resumes.schema import (
    RESUME_STYLE_OPTIONS,
    ResumeBasicInfo,
    ResumeContent,
    ResumeDetail,
    ResumeEducationEntry,
    ResumeExportPayload,
    ResumeGenerateRequest,
    ResumeInternshipEntry,
    ResumeJobIntention,
    ResumeProjectEntry,
    ResumeStoredPayload,
    ResumeUpdateRequest,
    merge_resume_content,
)
from app.modules.student_profile.models import ResumeRecord, StudentProfileRecord


TECH_FRONTEND = ["React", "TypeScript", "JavaScript", "HTML", "CSS", "Vite"]
TECH_BACKEND = ["Python", "FastAPI", "MySQL", "Redis", "SQL", "Docker"]
TECH_FULLSTACK = ["React", "TypeScript", "Python", "FastAPI", "MySQL", "Redis"]
CITY_MARKERS = ["深圳", "上海", "北京", "广州", "杭州", "成都", "武汉", "西安", "南京", "苏州"]
BANNED_SNIPPETS = ["Card5", "Card6", "系统模块", "模块名", "???", "？？？", "????"]


async def ensure_resume_tables(session: AsyncSession) -> None:
    async with session.bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def _get_student_record_or_raise(session: AsyncSession, student_profile_id: int) -> StudentProfileRecord:
    record = await session.get(StudentProfileRecord, student_profile_id)
    if record is None:
        raise AppException(
            message=f"Student profile {student_profile_id} does not exist",
            error_code="resume_student_profile_not_found",
            status_code=404,
        )
    await session.refresh(record)
    return record


async def _get_generated_resume_record_or_raise(session: AsyncSession, resume_id: int) -> ResumeRecord:
    record = await session.get(ResumeRecord, resume_id)
    if record is None:
        raise AppException(
            message=f"Resume {resume_id} does not exist",
            error_code="resume_not_found",
            status_code=404,
        )
    await session.refresh(record)
    source_payload = record.source_payload or {}
    if record.source_type != "generated" or source_payload.get("kind") != "generated_resume":
        raise AppException(
            message=f"Resume {resume_id} is not a generated resume record",
            error_code="resume_not_found",
            status_code=404,
        )
    return record


def _safe_text(value: Any) -> str:
    text = normalize_text(value, default="")
    if text in {"未明确", "未知", "null", "None"}:
        return ""
    text = re.sub(r"[?？]{2,}", "", text)
    for snippet in BANNED_SNIPPETS:
        text = text.replace(snippet, "")
    return re.sub(r"\s+", " ", text).strip(" ，,。；;、")


def _safe_list(values: Iterable[Any]) -> list[str]:
    cleaned = [_safe_text(item) for item in values]
    return [item for item in unique_keep_order(cleaned) if item]


def _job_track(target_job: str) -> str:
    lowered = _safe_text(target_job).lower()
    if "前端" in lowered or "frontend" in lowered:
        return "frontend"
    if "全栈" in lowered or "full stack" in lowered or "fullstack" in lowered:
        return "fullstack"
    if "后端" in lowered or "backend" in lowered or "python" in lowered or "java" in lowered:
        return "backend"
    return "backend"


def _preferred_skills_for_track(track: str) -> list[str]:
    if track == "frontend":
        return TECH_FRONTEND
    if track == "fullstack":
        return TECH_FULLSTACK
    return TECH_BACKEND


def _extract_city(student_payload: dict[str, Any], target_job: str) -> str:
    corpus = " ".join(
        [
            _safe_text(student_payload.get("career_intention")),
            _safe_text(student_payload.get("summary")),
            _safe_text(target_job),
            _safe_text(student_payload.get("student_work")),
            _safe_text(student_payload.get("internships")),
            _safe_text(student_payload.get("projects")),
        ]
    )
    for marker in CITY_MARKERS:
        if marker in corpus:
            return marker
    return ""


def _prioritize_skills(raw_skills: list[str], target_job: str) -> list[str]:
    skills = _safe_list(raw_skills)
    track = _job_track(target_job)
    preferred = _preferred_skills_for_track(track)
    ordered: list[str] = []
    lowered_map = {skill.lower(): skill for skill in skills}
    for skill in preferred:
        matched = lowered_map.get(skill.lower())
        if matched and matched not in ordered:
            ordered.append(matched)
    for skill in skills:
        if skill not in ordered:
            ordered.append(skill)
    return ordered[:12]


def _ability_highlights(student_payload: dict[str, Any]) -> list[str]:
    scores = student_payload.get("ability_scores") or {}
    label_map = {
        "professional_skills": "专业技能扎实",
        "innovation": "具备创新实践意识",
        "learning": "学习能力较强",
        "stress_tolerance": "适应节奏能力较好",
        "communication": "具备团队协作与沟通基础",
        "internship_ability": "具备岗位实践基础",
    }
    ranked = sorted(scores.items(), key=lambda item: float(item[1]), reverse=True)
    return [label_map.get(key, key) for key, _score in ranked[:2] if key in label_map]


def _build_summary(student_record: StudentProfileRecord, student_payload: dict[str, Any], target_job: str, skills: list[str]) -> str:
    track = _job_track(target_job)
    project_count = len(student_payload.get("projects") or [])
    internship_count = len(student_payload.get("internships") or [])
    education_bits = [part for part in [_safe_text(student_record.major), _safe_text(student_record.education), _safe_text(student_record.grade)] if part]
    education = "，".join(education_bits)
    strengths = _ability_highlights(student_payload)
    leading_skills = "、".join(skills[:4])

    if track == "frontend":
        focus = "重点突出 React 组件开发、页面交互实现与前后端联调能力"
    elif track == "fullstack":
        focus = "兼顾前端页面实现与后端接口开发，能够完成业务闭环落地"
    else:
        focus = "重点突出 Python 后端开发、接口设计与数据库能力"

    parts = [
        f"{education or '技术方向候选人'}，目标岗位为{target_job}。",
        f"具备 {leading_skills} 等技术基础，{focus}。" if leading_skills else f"目标岗位为{target_job}，{focus}。",
        f"已积累 {project_count} 段项目经历、{internship_count} 段实习/实践经历。",
    ]
    if strengths:
        parts.append(f"综合表现上，{ '、'.join(strengths) }。")
    return _safe_text("".join(parts))


def _project_stack(project: dict[str, Any], skills: list[str], target_job: str) -> list[str]:
    project_text = " ".join([_safe_text(project.get("name")), _safe_text(project.get("description"))]).lower()
    ordered = _prioritize_skills(skills, target_job)
    stack = [skill for skill in ordered if skill.lower() in project_text]
    if stack:
        return stack[:6]
    return ordered[:6]


def _build_project_highlights(project: dict[str, Any], target_job: str, skills: list[str]) -> list[str]:
    track = _job_track(target_job)
    project_name = _safe_text(project.get("name")) or "项目"
    description = _safe_text(project.get("description"))
    role = _safe_text(project.get("role")) or ("项目负责人" if track == "fullstack" else "核心开发成员")
    stack = _project_stack(project, skills, target_job)
    highlights: list[str] = []
    if description:
        highlights.append(description)
    if track == "frontend":
        highlights.append(f"围绕 {project_name} 完成前端页面实现、组件拆分与接口联调，提升页面交互与可用性。")
    elif track == "fullstack":
        highlights.append(f"围绕 {project_name} 负责前后端协同开发，覆盖页面交互、接口设计与数据流转。")
    else:
        highlights.append(f"围绕 {project_name} 参与后端接口开发、数据处理与服务联调，支撑核心业务流程。")
    if stack:
        highlights.append(f"项目中主要使用 { '、'.join(stack[:5]) } 完成功能实现与工程交付。")
    if role:
        highlights.append(f"在项目中承担 {role} 职责，能够推进功能落地与问题排查。")
    return _safe_list(highlights)[:4]


def _build_internship_highlights(internship: dict[str, Any], target_job: str, skills: list[str]) -> list[str]:
    track = _job_track(target_job)
    description = _safe_text(internship.get("description"))
    stack = _prioritize_skills(skills, target_job)
    highlights: list[str] = []
    if description:
        highlights.append(description)
    if track == "frontend":
        highlights.append("参与业务页面开发、需求联调与问题修复，具备基础前端交付意识。")
    elif track == "fullstack":
        highlights.append("参与前后端协作开发，能够基于需求完成页面、接口与数据联动。")
    else:
        highlights.append("参与接口开发、接口联调与数据库相关工作，具备基础后端工程实践经验。")
    if stack:
        highlights.append(f"实习期间持续使用 { '、'.join(stack[:4]) } 等技术栈完成开发和排查工作。")
    return _safe_list(highlights)[:3]


def _build_extras(student_payload: dict[str, Any], target_job: str, skills: list[str]) -> list[str]:
    extras: list[str] = []
    extras.extend(_safe_list(student_payload.get("certificates") or []))
    for competition in student_payload.get("competitions") or []:
        if isinstance(competition, dict):
            text = " · ".join(part for part in [_safe_text(competition.get("name")), _safe_text(competition.get("award"))] if part)
            if text:
                extras.append(text)
    for work in student_payload.get("student_work") or []:
        if isinstance(work, dict):
            text = " · ".join(part for part in [_safe_text(work.get("organization")), _safe_text(work.get("role")), _safe_text(work.get("description"))] if part)
            if text:
                extras.append(text)
    innovation_items = _safe_list(student_payload.get("innovation_experiences") or [])
    extras.extend(innovation_items[:3])
    if not extras:
        track = _job_track(target_job)
        if track == "frontend":
            extras.append("具备面向前端岗位的组件化开发与页面联调意识。")
        elif track == "fullstack":
            extras.append("具备从页面到接口的完整业务闭环实现意识。")
        else:
            extras.append("具备面向后端岗位的接口开发与数据处理实践基础。")
    return _safe_list(extras)[:6]


def _build_resume_content(student_record: StudentProfileRecord, target_job: str, style: str) -> ResumeContent:
    student_payload = student_record.profile_json or {}
    skills = _prioritize_skills(student_payload.get("skills") or [], target_job)
    target_city = _extract_city(student_payload, target_job)

    basic_info = ResumeBasicInfo(
        student_name=_safe_text(student_payload.get("student_name")),
        student_id=student_record.student_id,
        school=_safe_text(student_record.school or student_payload.get("school")),
        major=_safe_text(student_record.major or student_payload.get("major")),
        education=_safe_text(student_record.education or student_payload.get("education")),
        grade=_safe_text(student_record.grade or student_payload.get("grade")),
    )
    if not basic_info.student_name:
        basic_info.student_name = student_record.student_id

    education = [
        ResumeEducationEntry(
            school=basic_info.school,
            major=basic_info.major,
            education=basic_info.education,
            grade=basic_info.grade,
            highlights=_safe_list([
                student_payload.get("career_intention"),
                f"面向 {target_job} 方向持续完善项目与实习经历。",
            ]),
        )
    ]

    projects = []
    for raw in student_payload.get("projects") or []:
        if not isinstance(raw, dict):
            continue
        projects.append(
            ResumeProjectEntry(
                name=_safe_text(raw.get("name")),
                role=_safe_text(raw.get("role")),
                highlights=_build_project_highlights(raw, target_job, skills),
                tech_stack=_project_stack(raw, skills, target_job),
            )
        )

    internships = []
    for raw in student_payload.get("internships") or []:
        if not isinstance(raw, dict):
            continue
        internships.append(
            ResumeInternshipEntry(
                company=_safe_text(raw.get("company")),
                role=_safe_text(raw.get("role")),
                duration="3个月" if "3个月" in _safe_text(raw.get("description")) else "",
                highlights=_build_internship_highlights(raw, target_job, skills),
            )
        )

    content = ResumeContent(
        basic_info=basic_info,
        job_intention=ResumeJobIntention(target_job=target_job, target_city=target_city, style=style),
        summary=_build_summary(student_record, student_payload, target_job, skills),
        education=education,
        skills=skills,
        projects=projects,
        internships=internships,
        extras=_build_extras(student_payload, target_job, skills),
    )
    return ResumeContent.model_validate(content.model_dump(mode="json"))


def _render_markdown(detail: ResumeDetail) -> str:
    content = detail.content
    lines: list[str] = [f"# {content.basic_info.student_name or detail.student_id}", ""]
    lines.extend(
        [
            f"- 求职方向：{content.job_intention.target_job}",
            f"- 目标城市：{content.job_intention.target_city}" if content.job_intention.target_city else "- 目标城市：待沟通",
            f"- 学校 / 专业：{ ' / '.join(part for part in [content.basic_info.school, content.basic_info.major] if part) or '待补充' }",
            f"- 学历 / 年级：{ ' / '.join(part for part in [content.basic_info.education, content.basic_info.grade] if part) or '待补充' }",
            "",
            "## 个人概述",
            "",
            content.summary,
            "",
            "## 教育经历",
            "",
        ]
    )
    for item in content.education:
        title = " / ".join(part for part in [item.school, item.major, item.education, item.grade] if part)
        lines.append(f"### {title or '教育经历'}")
        lines.extend([f"- {highlight}" for highlight in item.highlights] or ["- 持续完善技术项目与岗位定制材料"]) 
        lines.append("")

    lines.extend(["## 专业技能", ""])
    lines.extend([f"- {skill}" for skill in content.skills] or ["- 待补充"])
    lines.append("")

    lines.extend(["## 项目经历", ""])
    if content.projects:
        for item in content.projects:
            lines.append(f"### {item.name or '项目经历'}")
            if item.role:
                lines.append(f"- 角色：{item.role}")
            if item.tech_stack:
                lines.append(f"- 技术栈：{'、'.join(item.tech_stack)}")
            lines.extend(f"- {highlight}" for highlight in item.highlights)
            lines.append("")
    else:
        lines.extend(["- 暂无项目经历", ""])

    lines.extend(["## 实习经历", ""])
    if content.internships:
        for item in content.internships:
            lines.append(f"### {item.company or '实习经历'}")
            if item.role:
                lines.append(f"- 岗位：{item.role}")
            if item.duration:
                lines.append(f"- 时长：{item.duration}")
            lines.extend(f"- {highlight}" for highlight in item.highlights)
            lines.append("")
    else:
        lines.extend(["- 暂无实习经历", ""])

    lines.extend(["## 补充信息", ""])
    lines.extend([f"- {item}" for item in content.extras] or ["- 暂无补充信息"])
    return "\n".join(line for line in lines if line is not None).strip()


def _stored_payload_from_detail(detail: ResumeDetail) -> ResumeStoredPayload:
    return ResumeStoredPayload(
        student_profile_id=detail.student_profile_id,
        student_id=detail.student_id,
        target_job=detail.target_job,
        style=detail.style,
        content=detail.content,
        markdown_content=detail.markdown_content,
        html_content=detail.html_content,
    )


def _build_resume_detail(record: ResumeRecord) -> ResumeDetail:
    payload = ResumeStoredPayload.model_validate(record.source_payload or {})
    return ResumeDetail(
        resume_id=record.id,
        student_profile_id=payload.student_profile_id,
        student_id=payload.student_id,
        target_job=payload.target_job,
        style=payload.style,
        content=payload.content,
        markdown_content=payload.markdown_content,
        html_content=payload.html_content,
        created_at=record.created_at,
    )


def _rebuild_detail(*, resume_id: int, student_profile_id: int, student_id: str, target_job: str, style: str, content: ResumeContent, created_at: datetime | None) -> ResumeDetail:
    detail = ResumeDetail(
        resume_id=resume_id,
        student_profile_id=student_profile_id,
        student_id=student_id,
        target_job=target_job,
        style=style,
        content=content,
        markdown_content="",
        html_content="",
        created_at=created_at,
    )
    detail.markdown_content = _render_markdown(detail)
    from app.modules.resumes.exporters import build_resume_html

    detail.html_content = build_resume_html(detail)
    return detail


async def generate_resume(session: AsyncSession, request: ResumeGenerateRequest) -> ResumeDetail:
    student_record = await _get_student_record_or_raise(session, request.student_profile_id)
    content = _build_resume_content(student_record, request.target_job, request.style)
    detail = _rebuild_detail(
        resume_id=0,
        student_profile_id=student_record.id,
        student_id=student_record.student_id,
        target_job=request.target_job,
        style=request.style,
        content=content,
        created_at=None,
    )
    if not request.persist:
        return detail

    await ensure_resume_tables(session)
    stored_payload = _stored_payload_from_detail(detail)
    filename_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", f"{student_record.student_id}-{request.target_job}-resume").strip("-") or "resume"
    record = ResumeRecord(
        student_id=student_record.student_id,
        source_type="generated",
        resume_filename=f"{filename_slug}.md",
        resume_text=detail.markdown_content,
        manual_form_payload=detail.content.model_dump(mode="json"),
        supplement_text=request.target_job,
        basic_info_payload=detail.content.basic_info.model_dump(mode="json"),
        normalized_text=detail.markdown_content,
        source_payload=stored_payload.model_dump(mode="json"),
    )
    session.add(record)
    await session.flush()
    await session.commit()
    await session.refresh(record)
    return _build_resume_detail(record)


async def get_resume(session: AsyncSession, resume_id: int) -> ResumeDetail:
    record = await _get_generated_resume_record_or_raise(session, resume_id)
    return _build_resume_detail(record)


async def update_resume(session: AsyncSession, resume_id: int, request: ResumeUpdateRequest) -> ResumeDetail:
    record = await _get_generated_resume_record_or_raise(session, resume_id)
    stored = ResumeStoredPayload.model_validate(record.source_payload or {})
    content = merge_resume_content(stored.content, request)

    target_job = request.target_job or stored.target_job
    style = request.style or stored.style
    if request.job_intention is not None:
        target_job = request.job_intention.target_job or target_job
        style = request.job_intention.style or style

    content.job_intention.target_job = target_job
    content.job_intention.style = style

    detail = _rebuild_detail(
        resume_id=record.id,
        student_profile_id=stored.student_profile_id,
        student_id=stored.student_id,
        target_job=target_job,
        style=style,
        content=content,
        created_at=record.created_at,
    )
    stored_payload = _stored_payload_from_detail(detail)

    record.resume_text = detail.markdown_content
    record.manual_form_payload = detail.content.model_dump(mode="json")
    record.supplement_text = target_job
    record.basic_info_payload = detail.content.basic_info.model_dump(mode="json")
    record.normalized_text = detail.markdown_content
    record.source_payload = stored_payload.model_dump(mode="json")
    await session.commit()
    await session.refresh(record)
    return _build_resume_detail(record)


async def export_resume(session: AsyncSession, resume_id: int, export_format: str) -> ResumeExportPayload:
    from app.modules.resumes.exporters import build_export_payload

    resume = await get_resume(session, resume_id)
    return build_export_payload(resume.model_dump(mode="json"), export_format)
