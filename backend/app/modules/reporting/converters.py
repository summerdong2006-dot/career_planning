from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Mapping

from app.modules.matching.utils import normalize_list, normalize_text

STANDARD_REPORT_SECTION_KEYS = (
    "summary",
    "match",
    "gap",
    "plan_short",
    "plan_mid",
)

STANDARD_REPORT_SECTION_TITLES = {
    "summary": "总体分析",
    "match": "岗位匹配分析",
    "gap": "能力差距",
    "plan_short": "短期计划",
    "plan_mid": "中期计划",
}

LEGACY_SECTION_KEY_MAP = {
    "overview": "summary",
    "profile_diagnosis": "summary",
    "job_recommendations": "match",
    "risk_alerts": "gap",
    "action_plan": "plan_short",
    "career_paths": "plan_mid",
}


def join_content_blocks(*blocks: str) -> str:
    normalized = [normalize_text(block, default="").strip() for block in blocks]
    return "\n\n".join(block for block in normalized if block)


def render_bullet_block(items: list[str] | None) -> str:
    values = [item for item in normalize_list(items) if item]
    return "\n".join(f"- {item}" for item in values)


def render_action_block(action_items: list[Mapping[str, Any]] | None) -> str:
    lines: list[str] = []
    for raw_item in action_items or []:
        title = normalize_text(raw_item.get("title"), default="")
        description = normalize_text(raw_item.get("description"), default="")
        timeline = normalize_text(raw_item.get("timeline"), default="")
        priority = normalize_text(raw_item.get("priority"), default="")
        success_metric = normalize_text(raw_item.get("success_metric"), default="")
        if not title and not description:
            continue
        suffix_parts = [part for part in (timeline, priority, success_metric) if part]
        suffix = f"（{'；'.join(suffix_parts)}）" if suffix_parts else ""
        if title and description:
            lines.append(f"- {title}：{description}{suffix}")
        else:
            lines.append(f"- {title or description}{suffix}")
    return "\n".join(lines)


def compose_legacy_section_content(section_payload: Mapping[str, Any]) -> str:
    content = normalize_text(section_payload.get("content"), default="")
    if content:
        return content

    body_markdown = normalize_text(section_payload.get("body_markdown"), default="")
    summary = normalize_text(section_payload.get("summary"), default="")
    bullets = render_bullet_block(section_payload.get("bullets"))
    action_items = render_action_block(section_payload.get("action_items"))
    return join_content_blocks(body_markdown or summary, bullets, action_items)


def _coerce_date_string(value: Any) -> str:
    normalized = normalize_text(value, default="")
    if not normalized:
        return ""
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return normalized[:10]


def _infer_generated_at(payload: Mapping[str, Any]) -> str:
    meta = payload.get("meta") or {}
    generation_params = payload.get("generation_params") or {}
    return (
        _coerce_date_string(meta.get("generated_at"))
        or _coerce_date_string(generation_params.get("generated_at"))
        or _coerce_date_string(payload.get("created_at"))
        or _coerce_date_string(payload.get("updated_at"))
    )


def _normalize_meta(payload: Mapping[str, Any]) -> dict[str, str]:
    meta = payload.get("meta") or {}
    legacy_meta = payload.get("metadata") or {}
    student_id = normalize_text(meta.get("student_id") or legacy_meta.get("student_id"), default="")
    target_job = normalize_text(
        meta.get("target_job")
        or legacy_meta.get("primary_job_title")
        or legacy_meta.get("career_intention"),
        default="",
    )
    return {
        "student_id": student_id,
        "target_job": target_job,
        "generated_at": _infer_generated_at(payload),
    }


def _normalize_section_payload(section_payload: Mapping[str, Any]) -> dict[str, str]:
    key = normalize_text(section_payload.get("key") or section_payload.get("section_key"), default="")
    title = normalize_text(section_payload.get("title"), default="") or STANDARD_REPORT_SECTION_TITLES.get(key, key)
    content = compose_legacy_section_content(section_payload)
    return {"key": key, "title": title, "content": content}


def _render_recommendation_block(recommendations: list[Mapping[str, Any]]) -> str:
    lines: list[str] = []
    for recommendation in recommendations:
        job_title = normalize_text(recommendation.get("job_title"), default="")
        reason = normalize_text(recommendation.get("recommendation_reason"), default="")
        total_score = recommendation.get("total_score")
        missing_skills = "、".join(normalize_list(recommendation.get("missing_skills")))
        parts = [part for part in (reason, f"总分 {total_score}" if total_score is not None else "", missing_skills) if part]
        if job_title:
            lines.append(f"- {job_title}：{'；'.join(parts)}".rstrip("："))
    return "\n".join(lines)


def _render_gap_block(recommendations: list[Mapping[str, Any]]) -> str:
    seen: OrderedDict[str, None] = OrderedDict()
    for recommendation in recommendations:
        for skill in normalize_list(recommendation.get("missing_skills")):
            seen[f"核心技能缺口：{skill}"] = None
        for gap in normalize_list(recommendation.get("gap_analysis")):
            seen[gap] = None
        for risk in normalize_list(recommendation.get("risk_flags")):
            seen[f"风险：{risk}"] = None
    return "\n".join(f"- {item}" for item in seen.keys())


def _render_path_block(recommendations: list[Mapping[str, Any]]) -> str:
    lines: list[str] = []
    for recommendation in recommendations:
        for path in recommendation.get("career_paths") or []:
            nodes = normalize_list(path.get("nodes"))
            label = normalize_text(path.get("path_label"), default="")
            if nodes:
                lines.append(f"- {label or '职业路径'}：{' -> '.join(nodes)}")
    return "\n".join(lines)


def _build_sections_from_legacy(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    grouped_blocks: dict[str, list[str]] = {key: [] for key in STANDARD_REPORT_SECTION_KEYS}

    executive_summary = normalize_text(payload.get("executive_summary"), default="")
    if executive_summary:
        grouped_blocks["summary"].append(executive_summary)

    key_findings = render_bullet_block(payload.get("key_findings"))
    if key_findings:
        grouped_blocks["summary"].append(key_findings)

    for raw_section in payload.get("sections") or []:
        if not isinstance(raw_section, Mapping):
            continue
        legacy_key = normalize_text(raw_section.get("key") or raw_section.get("section_key"), default="")
        standard_key = LEGACY_SECTION_KEY_MAP.get(legacy_key, legacy_key)
        if not standard_key:
            continue
        block = compose_legacy_section_content(raw_section)
        if block:
            grouped_blocks.setdefault(standard_key, []).append(block)

    recommendations = payload.get("recommendations") or []
    if recommendations:
        recommendation_block = _render_recommendation_block(recommendations)
        if recommendation_block and not grouped_blocks["match"]:
            grouped_blocks["match"].append(recommendation_block)
        gap_block = _render_gap_block(recommendations)
        if gap_block and not grouped_blocks["gap"]:
            grouped_blocks["gap"].append(gap_block)
        path_block = _render_path_block(recommendations)
        if path_block and not grouped_blocks["plan_mid"]:
            grouped_blocks["plan_mid"].append(path_block)

    suggested_actions = render_action_block(payload.get("suggested_actions"))
    if suggested_actions and not grouped_blocks["plan_short"]:
        grouped_blocks["plan_short"].append(suggested_actions)

    return [
        {
            "key": key,
            "title": STANDARD_REPORT_SECTION_TITLES[key],
            "content": join_content_blocks(*grouped_blocks.get(key, [])),
        }
        for key in STANDARD_REPORT_SECTION_KEYS
    ]


def convert_report_json_to_section_based(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "meta": {"student_id": "", "target_job": "", "generated_at": ""},
            "sections": [
                {"key": key, "title": title, "content": ""}
                for key, title in STANDARD_REPORT_SECTION_TITLES.items()
            ],
        }

    if "content" in payload and isinstance(payload.get("content"), Mapping):
        base = convert_report_json_to_section_based(payload.get("content"))
        if not base["meta"]["generated_at"]:
            base["meta"]["generated_at"] = _infer_generated_at(payload)
        return base

    if "meta" in payload and "sections" in payload:
        meta = _normalize_meta(payload)
        meta.update(
            {
                "student_id": normalize_text((payload.get("meta") or {}).get("student_id"), default=meta["student_id"]),
                "target_job": normalize_text((payload.get("meta") or {}).get("target_job"), default=meta["target_job"]),
                "generated_at": normalize_text((payload.get("meta") or {}).get("generated_at"), default=meta["generated_at"]),
            }
        )
        sections = []
        for raw_section in payload.get("sections") or []:
            if isinstance(raw_section, Mapping):
                sections.append(_normalize_section_payload(raw_section))
        if sections:
            return {"meta": meta, "sections": sections}

    return {"meta": _normalize_meta(payload), "sections": _build_sections_from_legacy(payload)}
