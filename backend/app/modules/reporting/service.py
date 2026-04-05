from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.base import Base
from app.modules.matching.matcher import classify_match_category
from app.modules.matching.schema import JobMatchResult
from app.modules.matching.service import recommend_jobs_for_student
from app.modules.reporting.llm import build_reporting_llm_client
from app.modules.reporting.models import CareerReportRecord
from app.modules.reporting.schema import (
    CareerPathOption,
    CareerRecommendation,
    CareerReportContent,
    CareerReportDetail,
    CareerReportExportPayload,
    CareerReportGenerateRequest,
    CareerReportListResponse,
    CareerReportMeta,
    CareerReportMetaUpdate,
    CareerReportPutRequest,
    CareerReportSection,
    CareerReportSectionPutRequest,
    CareerReportSectionUpdate,
    CareerReportSummary,
    CareerReportUpdateRequest,
    REPORT_SECTION_KEYS,
    SECTION_TITLES,
    ReportActionItem,
    ReportCompletenessCheck,
    ReportCompletenessItem,
    ReportEditorSection,
    ReportEditorState,
    join_content_blocks,
    render_action_block,
    render_bullet_block,
)
from app.modules.student_profile.models import StudentProfileRecord
from app.services.job_graph import generate_career_paths

logger = get_logger(__name__)


async def ensure_reporting_tables(session: AsyncSession) -> None:
    async with session.bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def _next_report_version(session: AsyncSession, student_profile_id: int) -> int:
    await ensure_reporting_tables(session)
    result = await session.execute(
        select(func.max(CareerReportRecord.report_version)).where(
            CareerReportRecord.student_profile_id == student_profile_id
        )
    )
    current = result.scalar_one_or_none()
    return int(current or 0) + 1


async def _get_student_record_or_raise(session: AsyncSession, student_profile_id: int) -> StudentProfileRecord:
    record = await session.get(StudentProfileRecord, student_profile_id)
    if record is None:
        raise AppException(
            message=f"Student profile {student_profile_id} does not exist",
            error_code="career_report_student_profile_not_found",
            status_code=404,
        )
    await session.refresh(record)
    return record


async def _get_report_record_or_raise(session: AsyncSession, report_id: int) -> CareerReportRecord:
    record = await session.get(CareerReportRecord, report_id)
    if record is None:
        raise AppException(
            message=f"Career report {report_id} does not exist",
            error_code="career_report_not_found",
            status_code=404,
        )
    await session.refresh(record)
    return record


def _extract_missing_skills(match: JobMatchResult) -> list[str]:
    detail = match.dimension_details.get("skill")
    if detail is None or not isinstance(detail.details, dict):
        return []
    return list(dict.fromkeys(detail.details.get("missing_must_skills", [])))


def _extract_matched_skills(match: JobMatchResult) -> list[str]:
    detail = match.dimension_details.get("skill")
    if detail is None or not isinstance(detail.details, dict):
        return []
    values: list[str] = []
    for item in detail.details.get("must_matches", []):
        if item.get("matched"):
            values.append(item.get("required_skill") or item.get("matched_skill") or "")
    return [value for value in dict.fromkeys(values) if value]


def _pick_primary_match(matches: list[JobMatchResult], primary_job_id: int | None) -> JobMatchResult:
    if not matches:
        raise AppException(
            message="No match results available to build report",
            error_code="career_report_matches_not_found",
            status_code=404,
        )
    if primary_job_id is not None:
        selected = next((match for match in matches if match.job_id == primary_job_id), None)
        if selected is None:
            raise AppException(
                message=f"Primary job {primary_job_id} is not present in current top-k matches",
                error_code="career_report_primary_job_not_found",
                status_code=400,
            )
        return selected
    return matches[0]


async def _build_path_options(session: AsyncSession, match: JobMatchResult) -> list[CareerPathOption]:
    path_payload = await generate_career_paths(session, match.job_id)
    options: list[CareerPathOption] = []
    labels = ("纵向晋升路径", "横向迁移路径")
    for index, path in enumerate(path_payload.get("paths", [])):
        if len(path) < 2:
            continue
        label = labels[index] if index < len(labels) else f"发展路径 {index + 1}"
        rationale = f"基于 Card6 职业路径图谱，当前岗位可沿 {' -> '.join(path)} 演进。"
        options.append(
            CareerPathOption(
                path_label=label,
                nodes=path,
                rationale=rationale,
                source_job_id=match.job_id,
            )
        )
    return options


def _build_recommendation_actions(match: JobMatchResult, student_payload: dict[str, Any]) -> list[ReportActionItem]:
    actions: list[ReportActionItem] = []
    missing_skills = _extract_missing_skills(match)
    if missing_skills:
        actions.append(
            ReportActionItem(
                action_id=f"job-{match.job_id}-missing-skills",
                title=f"补齐 {missing_skills[0]} 等核心技能证据",
                description=f"围绕 {'、'.join(missing_skills[:3])} 各补 1 个项目或实习证据，再投递 {match.job_title}。",
                timeline="1-3 周",
                priority="high",
                success_metric=f"至少形成 1 份包含 {'、'.join(missing_skills[:2])} 的项目说明或作品链接",
                related_gap=f"缺少核心技能：{'、'.join(missing_skills[:3])}",
            )
        )
    if match.dimension_scores.soft_skill < 70:
        actions.append(
            ReportActionItem(
                action_id=f"job-{match.job_id}-soft-skill",
                title="补充沟通协作场景证据",
                description="在简历和面试故事中补充跨团队协作、汇报或推进落地的具体案例。",
                timeline="1-2 周",
                priority="medium",
                success_metric="形成 2 个 STAR 面试案例，并写入简历或作品集",
                related_gap="软技能证据不足",
            )
        )
    if student_payload.get("completeness_score", 0) < 70:
        actions.append(
            ReportActionItem(
                action_id=f"job-{match.job_id}-profile-completion",
                title="提升画像与简历完整度",
                description="优先补充技能清单、项目成果、实习职责和量化结果，避免匹配结果失真。",
                timeline="本周内",
                priority="high",
                success_metric="简历补齐 3 类缺失信息，并将完整度提升到 70 分以上",
                related_gap="学生画像完整度不足",
            )
        )
    if not actions:
        actions.append(
            ReportActionItem(
                action_id=f"job-{match.job_id}-deliver-project",
                title=f"围绕 {match.job_title} 准备针对性作品集",
                description="保留当前优势技能，同时把最能证明岗位匹配度的项目成果整理成可投递材料。",
                timeline="2 周",
                priority="medium",
                success_metric="完成 1 份岗位定制版简历和 1 份项目证明材料",
                related_gap="提升投递转化率",
            )
        )
    return actions[:3]


def _build_recommendation(
    match: JobMatchResult,
    student_payload: dict[str, Any],
    path_options: list[CareerPathOption],
) -> CareerRecommendation:
    return CareerRecommendation(
        match_id=match.match_id,
        job_id=match.job_id,
        job_profile_id=match.job_profile_id,
        job_title=match.job_title,
        category=classify_match_category(match) or "reserve",
        total_score=match.total_score,
        dimension_scores=match.dimension_scores.model_dump(),
        recommendation_reason=match.reason,
        matched_skills=_extract_matched_skills(match),
        missing_skills=_extract_missing_skills(match),
        gap_analysis=match.gap_analysis,
        risk_flags=match.risk_flags,
        evidence=match.evidence,
        key_actions=_build_recommendation_actions(match, student_payload),
        career_paths=path_options,
    )


def _ability_strengths(student_payload: dict[str, Any]) -> list[str]:
    ability_scores = student_payload.get("ability_scores") or {}
    pairs = sorted(ability_scores.items(), key=lambda item: float(item[1]), reverse=True)
    label_map = {
        "professional_skills": "专业技能",
        "innovation": "创新能力",
        "learning": "学习能力",
        "stress_tolerance": "抗压能力",
        "communication": "沟通能力",
        "internship_ability": "实习能力",
    }
    return [f"{label_map.get(key, key)} {round(float(score), 2)} 分" for key, score in pairs[:3]]


def _aggregate_gap_items(recommendations: Iterable[CareerRecommendation]) -> list[str]:
    counter: Counter[str] = Counter()
    for recommendation in recommendations:
        for skill in recommendation.missing_skills:
            counter[f"核心技能缺口：{skill}"] += 2
        for gap in recommendation.gap_analysis[:4]:
            counter[gap] += 1
    return [item for item, _count in counter.most_common(6)]


def _aggregate_risks(recommendations: Iterable[CareerRecommendation]) -> list[str]:
    counter: Counter[str] = Counter()
    for recommendation in recommendations:
        for risk in recommendation.risk_flags:
            counter[risk] += 1
    return [item for item, _count in counter.most_common(5)]


def _aggregate_report_actions(
    student_payload: dict[str, Any],
    primary_recommendation: CareerRecommendation,
    recommendations: list[CareerRecommendation],
) -> list[ReportActionItem]:
    actions: list[ReportActionItem] = []
    missing_items = student_payload.get("missing_items") or []
    if missing_items:
        top_missing = missing_items[0]
        actions.append(
            ReportActionItem(
                action_id="report-profile-fix",
                title=f"优先补齐{top_missing.get('label', '关键信息')}",
                description=top_missing.get("suggestion") or "补充缺失信息并重新生成画像与报告。",
                timeline="0-7 天",
                priority="high",
                success_metric="关键缺失项补齐后重新生成报告，确认匹配结果变化",
                related_gap=top_missing.get("label") or "画像缺口",
            )
        )
    primary_path = primary_recommendation.career_paths[0].nodes if primary_recommendation.career_paths else []
    if len(primary_path) >= 2:
        actions.append(
            ReportActionItem(
                action_id="report-path-prep",
                title=f"对齐下一站岗位 {primary_path[1]}",
                description=f"围绕主目标岗位的后续路径 {primary_path[0]} -> {primary_path[1]}，提前补充下一阶段需要的项目深度和业务复杂度。",
                timeline="30-60 天",
                priority="medium",
                success_metric=f"输出 1 份面向 {primary_path[1]} 的能力清单和项目改造计划",
                related_gap="路径晋升准备",
            )
        )
    category_counts = Counter(recommendation.category for recommendation in recommendations)
    actions.append(
        ReportActionItem(
            action_id="report-apply-strategy",
            title="按分层岗位执行投递策略",
            description=f"优先投递 {category_counts.get('match', 0)} 个匹配岗，穿插 {category_counts.get('safe', 0)} 个保底岗和 {category_counts.get('stretch', 0)} 个冲刺岗。",
            timeline="每周",
            priority="medium",
            success_metric="每周完成 8-12 个精准投递，并追踪面试转化率",
            related_gap="投递节奏管理",
        )
    )
    for action in primary_recommendation.key_actions:
        if len(actions) >= 4:
            break
        actions.append(action)
    return actions[:4]


def _is_short_timeline(timeline: str) -> bool:
    if any(keyword in timeline for keyword in ("30-60", "60 天", "1-3 月", "月")):
        return False
    return True


def _build_sections(
    student_record: StudentProfileRecord,
    recommendations: list[CareerRecommendation],
    primary_recommendation: CareerRecommendation,
    report_actions: list[ReportActionItem],
    generated_at: str,
) -> list[CareerReportSection]:
    student_payload = student_record.profile_json or {}
    strengths = _ability_strengths(student_payload)
    profile_gaps = [item.get("suggestion") or item.get("label") for item in student_payload.get("missing_items", [])][:4]
    gap_items = _aggregate_gap_items(recommendations)
    risks = _aggregate_risks(recommendations)

    short_actions = [action for action in report_actions if _is_short_timeline(action.timeline)] or report_actions[:2]
    mid_actions = [action for action in report_actions if not _is_short_timeline(action.timeline)] or report_actions[2:]

    recommendation_lines = [
        f"{recommendation.job_title}｜{recommendation.category}｜总分 {recommendation.total_score}｜关键短板：{'、'.join(recommendation.missing_skills[:3]) or '无明显核心技能缺口'}"
        for recommendation in recommendations
    ]
    path_lines = [
        f"{path.path_label}：{' -> '.join(path.nodes)}"
        for path in primary_recommendation.career_paths
        if path.nodes
    ]

    return [
    CareerReportSection(
        key="summary",
        title="一、总体评估",
        content=join_content_blocks(
            f"该学生当前推荐目标岗位为【{primary_recommendation.job_title}】，综合匹配得分为 {primary_recommendation.total_score} 分（生成时间：{generated_at}）。",
            render_bullet_block([
                f"学生画像完整度：{student_record.completeness_score}，竞争力：{student_record.competitiveness_score}",
                f"能力优势：{'；'.join(strengths) if strengths else '暂无明显优势'}",
                f"推荐理由：{primary_recommendation.recommendation_reason}",
            ])
        ),
    ),

    CareerReportSection(
        key="match",
        title="二、岗位匹配分析",
        content=join_content_blocks(
            "以下为当前推荐岗位匹配情况：",
            render_bullet_block([
                f"{rec.job_title}｜匹配度 {rec.total_score}｜短板：{'、'.join(rec.missing_skills[:3]) or '无明显短板'}"
                for rec in recommendations
            ])
        ),
    ),

    CareerReportSection(
        key="gap",
        title="三、能力差距分析",
        content=join_content_blocks(
            "当前主要能力短板如下：",
            render_bullet_block(
                gap_items if gap_items else ["暂无明显能力短板"]
            )
        ),
    ),

    CareerReportSection(
        key="plan_short",
        title="四、短期提升建议（1-4周）",
        content=join_content_blocks(
            "建议优先完成以下动作：",
            render_action_block([
                action.model_dump(mode="json") for action in short_actions
            ])
        ),
    ),

    CareerReportSection(
        key="plan_mid",
        title="五、中期发展路径（1-3个月）",
        content=join_content_blocks(
            "推荐职业发展路径：",
            render_bullet_block([
                f"{path.path_label}：{' -> '.join(path.nodes)}"
                for path in primary_recommendation.career_paths
            ]),
            render_action_block([
                action.model_dump(mode="json") for action in mid_actions
            ])
        ),
    ),
]


def _build_editor_state(report_title: str, sections: list[CareerReportSection]) -> ReportEditorState:
    return ReportEditorState(
        report_title=report_title,
        sections=[ReportEditorSection(section_key=section.key, title=section.title, content=section.content) for section in sections],
    )


def _build_reporting_llm_prompts(
    report_title: str,
    student_record: StudentProfileRecord,
    recommendations: list[CareerRecommendation],
    suggested_actions: list[ReportActionItem],
    content: CareerReportContent,
) -> tuple[str, str]:
    student_payload = student_record.profile_json or {}
    student_context = {
        "student_id": student_record.student_id,
        "name": student_payload.get("student_name"),
        "career_intention": student_payload.get("career_intention"),
        "education": {
            "school_name": student_payload.get("school_name"),
            "major": student_payload.get("major"),
            "degree": student_payload.get("degree"),
            "grade": student_payload.get("grade"),
        },
        "skills": student_payload.get("skills") or [],
        "certificates": student_payload.get("certificates") or [],
        "ability_scores": student_payload.get("ability_scores") or {},
        "completeness_score": student_record.completeness_score,
        "competitiveness_score": student_record.competitiveness_score,
        "projects": student_payload.get("projects") or [],
        "internships": student_payload.get("internships") or [],
        "raw_text_excerpt": (student_payload.get("raw_text") or "")[:1600],
    }
    recommendation_context = [
        {
            "job_title": item.job_title,
            "category": item.category,
            "total_score": item.total_score,
            "dimension_scores": item.dimension_scores,
            "recommendation_reason": item.recommendation_reason,
            "matched_skills": item.matched_skills[:6],
            "missing_skills": item.missing_skills[:6],
            "gap_analysis": item.gap_analysis[:6],
            "risk_flags": item.risk_flags[:4],
            "career_paths": [path.model_dump(mode="json") for path in item.career_paths],
        }
        for item in recommendations
    ]
    action_context = [item.model_dump(mode="json") for item in suggested_actions]
    section_context = [section.model_dump(mode="json") for section in content.sections]

    system_prompt = (
        "你是一名大学生职业规划顾问。"
        "请基于学生画像、人岗匹配结果和职业路径信息，生成一份可操作、可解释的中文职业发展报告。"
        "必须严格输出 JSON 对象，不要输出 markdown 代码块或额外说明。"
        "JSON 结构必须为："
        '{"report_title":"字符串","sections":[{"key":"summary","title":"字符串","content":"字符串"},'
        '{"key":"match","title":"字符串","content":"字符串"},'
        '{"key":"gap","title":"字符串","content":"字符串"},'
        '{"key":"plan_short","title":"字符串","content":"字符串"},'
        '{"key":"plan_mid","title":"字符串","content":"字符串"}]}。'
        "每个 section 的 key 必须保持固定，content 请使用自然中文，可包含简短列表，但不要返回空内容。"
        "内容要结合具体技能、能力得分、匹配差距和路径建议，避免空泛套话。"
    )
    user_prompt = json.dumps(
        {
            "report_title": report_title,
            "student": student_context,
            "recommendations": recommendation_context,
            "suggested_actions": action_context,
            "fallback_sections": section_context,
        },
        ensure_ascii=False,
        indent=2,
    )
    return system_prompt, user_prompt


async def _refine_report_with_llm(
    report_title: str,
    student_record: StudentProfileRecord,
    recommendations: list[CareerRecommendation],
    suggested_actions: list[ReportActionItem],
    content: CareerReportContent,
) -> tuple[str, CareerReportContent, str]:
    client = build_reporting_llm_client()
    provider_name = getattr(client, "provider_name", "heuristic")
    system_prompt, user_prompt = _build_reporting_llm_prompts(
        report_title=report_title,
        student_record=student_record,
        recommendations=recommendations,
        suggested_actions=suggested_actions,
        content=content,
    )
    payload = await client.extract(system_prompt, user_prompt)
    if payload is None:
        return report_title, content, "heuristic"

    next_title = str(payload.get("report_title") or report_title).strip() or report_title
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        logger.warning("Reporting LLM payload missing sections list")
        return report_title, content, "heuristic"

    original_map = {section.key: section for section in content.sections}
    sections: list[CareerReportSection] = []
    for key in REPORT_SECTION_KEYS:
        raw_section = next(
            (
                item for item in raw_sections
                if isinstance(item, dict) and str(item.get("key") or "").strip() == key
            ),
            None,
        )
        if raw_section is None:
            fallback = original_map[key]
            sections.append(fallback)
            continue
        title = str(raw_section.get("title") or original_map[key].title).strip() or original_map[key].title
        content_text = str(raw_section.get("content") or original_map[key].content).strip() or original_map[key].content
        sections.append(CareerReportSection(key=key, title=title, content=content_text))

    return next_title, CareerReportContent(meta=content.meta, sections=sections), provider_name


def _evaluate_completeness(
    content: CareerReportContent,
    student_record: StudentProfileRecord,
    recommendations: list[CareerRecommendation],
    suggested_actions: list[ReportActionItem],
) -> ReportCompletenessCheck:
    section_map = {section.key: section for section in content.sections}
    missing_sections = [key for key in REPORT_SECTION_KEYS if not section_map.get(key) or not section_map[key].content]
    checks = [
        ReportCompletenessItem(key="meta_present", passed=bool(content.meta.student_id and content.meta.target_job), message="报告 meta 信息完整"),
        ReportCompletenessItem(key="required_sections_present", passed=not missing_sections, message="五个核心章节完整"),
        ReportCompletenessItem(key="recommendations_present", passed=bool(recommendations), message="显式包含岗位推荐结果"),
        ReportCompletenessItem(key="career_paths_present", passed=any(item.career_paths for item in recommendations), message="显式包含职业路径信息"),
        ReportCompletenessItem(key="action_plan_present", passed=bool(suggested_actions), message="包含可执行行动计划"),
    ]
    passed_count = sum(1 for item in checks if item.passed)
    score = round((passed_count / len(checks)) * 100, 2)
    warnings: list[str] = []
    if student_record.completeness_score < 60:
        warnings.append("学生画像完整度偏低，报告建议仅作为初步决策依据。")
    if any(item.total_score < 60 for item in recommendations):
        warnings.append("部分推荐岗位属于低分冲刺方向，投递前应先补齐核心差距。")
    if not any(item.evidence for item in recommendations):
        warnings.append("推荐说明缺少足够证据片段，建议回看原始画像和 JD。")
    return ReportCompletenessCheck(
        score=score,
        is_complete=score >= 80 and not missing_sections,
        missing_sections=missing_sections,
        warnings=warnings,
        checks=checks,
    )


def _render_markdown(report_title: str, content: CareerReportContent) -> str:
    lines: list[str] = [f"# {report_title}", ""]
    lines.extend(
        [
            f"- 学生 ID：{content.meta.student_id or '未明确'}",
            f"- 目标岗位：{content.meta.target_job or '未明确'}",
            f"- 生成时间：{content.meta.generated_at or '未记录'}",
            "",
        ]
    )
    for section in content.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if section.content:
            lines.append(section.content)
        lines.append("")
    return "\n".join(lines).strip()


def _render_html(report_title: str, markdown_content: str) -> str:
    from app.modules.reporting.exporters import build_inline_html

    return build_inline_html(markdown_content, report_title)


def _build_source_snapshot(
    student_record: StudentProfileRecord,
    matches: list[JobMatchResult],
    recommendations: list[CareerRecommendation],
    suggested_actions: list[ReportActionItem],
    report_generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "student_profile": student_record.profile_json or {},
        "matches": [match.model_dump(mode="json") for match in matches],
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
        "suggested_actions": [item.model_dump(mode="json") for item in suggested_actions],
        "report_generation": report_generation or {},
    }


def _load_recommendations(record: CareerReportRecord) -> list[CareerRecommendation]:
    payload = (record.source_snapshot or {}).get("recommendations") or []
    return [CareerRecommendation.model_validate(item) for item in payload]


def _load_suggested_actions(record: CareerReportRecord) -> list[ReportActionItem]:
    payload = (record.source_snapshot or {}).get("suggested_actions") or []
    return [ReportActionItem.model_validate(item) for item in payload]


def _normalize_report_content(record: CareerReportRecord) -> CareerReportContent:
    return CareerReportContent.model_validate(record.report_payload or {})


def _build_report_detail(record: CareerReportRecord) -> CareerReportDetail:
    return CareerReportDetail(
        report_id=record.id,
        student_profile_id=record.student_profile_id,
        report_version=record.report_version,
        report_title=record.report_title,
        status=record.status,
        primary_match_result_id=record.primary_match_result_id,
        primary_job_profile_id=record.primary_job_profile_id,
        primary_job_id=record.primary_job_id,
        source_match_result_ids=record.source_match_result_ids or [],
        content=_normalize_report_content(record),
        recommendations=_load_recommendations(record),
        suggested_actions=_load_suggested_actions(record),
        editor_state=ReportEditorState.model_validate(record.editor_state or {}),
        completeness_check=ReportCompletenessCheck.model_validate(record.completeness_check or {}),
        markdown_content=record.markdown_content,
        html_content=record.html_content,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _ordered_sections(sections: list[CareerReportSection]) -> list[CareerReportSection]:
    section_map = {section.key: section for section in sections}
    return [section_map[key] for key in REPORT_SECTION_KEYS if key in section_map]


def _merge_report_meta(existing: CareerReportMeta, update: CareerReportMetaUpdate | None) -> CareerReportMeta:
    if update is None:
        return existing
    payload = existing.model_dump(mode="json")
    payload.update(update.model_dump(exclude_none=True))
    return CareerReportMeta.model_validate(payload)


def _merge_report_sections(
    existing_sections: list[CareerReportSection],
    updates: list[CareerReportSectionUpdate],
    report_id: int,
) -> list[CareerReportSection]:
    section_map = {section.key: section.model_copy(deep=True) for section in existing_sections}
    for update in updates:
        target = section_map.get(update.section_key)
        if target is None:
            raise AppException(
                message=f"Section {update.section_key} does not exist in report {report_id}",
                error_code="career_report_section_not_found",
                status_code=404,
            )
        if update.title is not None:
            target.title = update.title
        if update.content is not None:
            target.content = update.content
        section_map[update.section_key] = target
    return _ordered_sections(list(section_map.values()))


def _rebuild_report_record(
    record: CareerReportRecord,
    student_record: StudentProfileRecord,
    content: CareerReportContent,
) -> None:
    recommendations = _load_recommendations(record)
    suggested_actions = _load_suggested_actions(record)
    record.report_payload = content.model_dump(mode="json")
    record.editor_state = _build_editor_state(record.report_title, content.sections).model_dump(mode="json")
    record.completeness_check = _evaluate_completeness(content, student_record, recommendations, suggested_actions).model_dump(mode="json")
    record.markdown_content = _render_markdown(record.report_title, content)
    record.html_content = _render_html(record.report_title, record.markdown_content)


async def generate_career_report(
    session: AsyncSession,
    request: CareerReportGenerateRequest,
) -> CareerReportDetail:
    student_record = await _get_student_record_or_raise(session, request.student_profile_id)
    recommended = await recommend_jobs_for_student(
        session=session,
        student_profile_id=request.student_profile_id,
        top_k=request.top_k,
        weights=request.weights,
        persist=request.persist_matches,
    )
    matches = recommended.matches
    primary_match = _pick_primary_match(matches, request.primary_job_id)
    student_payload = student_record.profile_json or {}

    recommendations: list[CareerRecommendation] = []
    for match in matches:
        recommendations.append(_build_recommendation(match, student_payload, await _build_path_options(session, match)))

    primary_recommendation = next(item for item in recommendations if item.job_id == primary_match.job_id)
    suggested_actions = _aggregate_report_actions(student_payload, primary_recommendation, recommendations)
    generated_at = datetime.now(timezone.utc).date().isoformat()
    content = CareerReportContent(
        meta=CareerReportMeta(
            student_id=student_record.student_id,
            target_job=primary_recommendation.job_title,
            generated_at=generated_at,
        ),
        sections=_build_sections(student_record, recommendations, primary_recommendation, suggested_actions, generated_at),
    )
    report_title = request.report_title or f"{student_record.student_id} 职业发展报告"
    report_title, content, report_generator = await _refine_report_with_llm(
        report_title=report_title,
        student_record=student_record,
        recommendations=recommendations,
        suggested_actions=suggested_actions,
        content=content,
    )
    completeness_check = _evaluate_completeness(content, student_record, recommendations, suggested_actions)
    markdown_content = _render_markdown(report_title, content)
    html_content = _render_html(report_title, markdown_content)
    report_version = await _next_report_version(session, student_record.id)
    editor_state = _build_editor_state(report_title, content.sections)
    source_snapshot = _build_source_snapshot(
        student_record,
        matches,
        recommendations,
        suggested_actions,
        report_generation={"generator": report_generator},
    )

    if not request.persist:
        return CareerReportDetail(
            report_id=0,
            student_profile_id=student_record.id,
            report_version=report_version,
            report_title=report_title,
            status="draft",
            primary_match_result_id=primary_match.match_id,
            primary_job_profile_id=primary_match.job_profile_id,
            primary_job_id=primary_match.job_id,
            source_match_result_ids=[match.match_id for match in matches if match.match_id is not None],
            content=content,
            recommendations=recommendations,
            suggested_actions=suggested_actions,
            editor_state=editor_state,
            completeness_check=completeness_check,
            markdown_content=markdown_content,
            html_content=html_content,
            created_at=None,
            updated_at=None,
        )

    await ensure_reporting_tables(session)
    record = CareerReportRecord(
        student_profile_id=student_record.id,
        primary_match_result_id=primary_match.match_id,
        primary_job_profile_id=primary_match.job_profile_id,
        primary_job_id=primary_match.job_id,
        report_version=report_version,
        report_title=report_title,
        status="draft",
        source_match_result_ids=[match.match_id for match in matches if match.match_id is not None],
        generation_params={
            "top_k": request.top_k,
            "primary_job_id": request.primary_job_id,
            "persist_matches": request.persist_matches,
            "weights": request.weights.model_dump(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_generator": report_generator,
        },
        source_snapshot=source_snapshot,
        report_payload=content.model_dump(mode="json"),
        editor_state=editor_state.model_dump(mode="json"),
        completeness_check=completeness_check.model_dump(mode="json"),
        markdown_content=markdown_content,
        html_content=html_content,
    )
    session.add(record)
    await session.flush()
    await session.commit()
    await session.refresh(record)
    return _build_report_detail(record)


async def get_career_report(session: AsyncSession, report_id: int) -> CareerReportDetail:
    record = await _get_report_record_or_raise(session, report_id)
    return _build_report_detail(record)


async def get_latest_career_report_for_student(
    session: AsyncSession,
    student_profile_id: int,
) -> CareerReportDetail:
    await ensure_reporting_tables(session)
    result = await session.execute(
        select(CareerReportRecord)
        .where(CareerReportRecord.student_profile_id == student_profile_id)
        .order_by(CareerReportRecord.report_version.desc(), CareerReportRecord.id.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise AppException(
            message=f"No career report exists for student profile {student_profile_id}",
            error_code="career_report_not_found",
            status_code=404,
        )
    return _build_report_detail(record)


async def list_career_reports_for_student(
    session: AsyncSession,
    student_profile_id: int,
) -> CareerReportListResponse:
    await ensure_reporting_tables(session)
    result = await session.execute(
        select(CareerReportRecord)
        .where(CareerReportRecord.student_profile_id == student_profile_id)
        .order_by(CareerReportRecord.report_version.desc(), CareerReportRecord.id.desc())
    )
    items = []
    for record in result.scalars().all():
        content = _normalize_report_content(record)
        items.append(
            CareerReportSummary(
                report_id=record.id,
                student_profile_id=record.student_profile_id,
                report_version=record.report_version,
                report_title=record.report_title,
                status=record.status,
                primary_job_title=content.meta.target_job or "未明确",
                completeness_score=(record.completeness_check or {}).get("score", 0.0),
                updated_at=record.updated_at,
            )
        )
    return CareerReportListResponse(items=items)


async def update_career_report_section(
    session: AsyncSession,
    report_id: int,
    section_key: str,
    request: CareerReportSectionPutRequest,
) -> CareerReportDetail:
    record = await _get_report_record_or_raise(session, report_id)
    student_record = await _get_student_record_or_raise(session, record.student_profile_id)
    content = _normalize_report_content(record)
    content.sections = _merge_report_sections(
        content.sections,
        [CareerReportSectionUpdate(section_key=section_key, title=request.title, content=request.content)],
        report_id,
    )
    _rebuild_report_record(record, student_record, content)
    await session.commit()
    await session.refresh(record)
    return _build_report_detail(record)


async def put_career_report(
    session: AsyncSession,
    report_id: int,
    request: CareerReportPutRequest,
) -> CareerReportDetail:
    record = await _get_report_record_or_raise(session, report_id)
    student_record = await _get_student_record_or_raise(session, record.student_profile_id)
    content = _normalize_report_content(record)

    content.meta = _merge_report_meta(content.meta, request.meta)
    if request.sections:
        content.sections = _merge_report_sections(content.sections, request.sections, report_id)

    if request.report_title is not None:
        record.report_title = request.report_title
    if request.status is not None:
        record.status = request.status

    _rebuild_report_record(record, student_record, content)
    await session.commit()
    await session.refresh(record)
    return _build_report_detail(record)


async def update_career_report(
    session: AsyncSession,
    report_id: int,
    request: CareerReportUpdateRequest,
) -> CareerReportDetail:
    return await put_career_report(
        session,
        report_id,
        CareerReportPutRequest(
            report_title=request.report_title,
            status=request.status,
            sections=request.section_updates,
        ),
    )


async def export_career_report(
    session: AsyncSession,
    report_id: int,
    export_format: str,
) -> CareerReportExportPayload:
    from app.modules.reporting.exporters import build_export_payload

    report = await get_career_report(session, report_id)
    return build_export_payload(report.model_dump(mode="json"), export_format)
