from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.matching.config import DEFAULT_TOP_K, TEXT_DEFAULT
from app.modules.matching.schema import MatchingWeights
from app.modules.matching.utils import clamp_score, normalize_list, normalize_text

REPORT_SECTION_KEYS = (
    "summary",
    "match",
    "gap",
    "plan_short",
    "plan_mid",
)
SUPPORTED_EXPORT_FORMATS = ("markdown", "html", "json", "pdf")
SECTION_TITLES = {
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


def normalize_report_multiline_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        for item in value:
            text = normalize_report_multiline_text(item, default="")
            if text:
                return text
        return default
    if isinstance(value, dict):
        return default
    text = str(value).replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = "\n".join(line for line in text.split("\n"))
    text = text.strip()
    return text or default


def join_content_blocks(*blocks: str) -> str:
    normalized = [normalize_report_multiline_text(block, default="").strip() for block in blocks]
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

        joined_suffix = " / ".join(suffix_parts) if suffix_parts else ""
        suffix = f"（{joined_suffix}）" if joined_suffix else ""
        if title and description:
            lines.append(f"- {title}：{description}{suffix}")
        else:
            lines.append(f"- {title or description}{suffix}")
    return "\n".join(lines)


def _coerce_date_string(value: Any) -> str:
    normalized = normalize_text(value, default="")
    if not normalized:
        return ""
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return normalized[:10]


def _infer_generated_at(payload: Mapping[str, Any]) -> str:
    meta = _to_plain_dict(payload.get("meta"))
    generation_params = _to_plain_dict(payload.get("generation_params"))
    return (
        _coerce_date_string(meta.get("generated_at"))
        or _coerce_date_string(generation_params.get("generated_at"))
        or _coerce_date_string(payload.get("created_at"))
        or _coerce_date_string(payload.get("updated_at"))
    )


def _compose_section_content(section_payload: Mapping[str, Any]) -> str:
    content = normalize_report_multiline_text(section_payload.get("content"), default="")
    if content:
        return content
    main_content = normalize_report_multiline_text(section_payload.get("body_markdown"), default="") or normalize_report_multiline_text(
        section_payload.get("summary"),
        default="",
    )
    bullets = render_bullet_block(section_payload.get("bullets"))
    action_items = render_action_block(section_payload.get("action_items"))
    return join_content_blocks(main_content, bullets, action_items)


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        return dict(dumped) if isinstance(dumped, Mapping) else {}
    return {}


def _normalize_meta(payload: Mapping[str, Any]) -> dict[str, str]:
    meta = _to_plain_dict(payload.get("meta"))
    legacy_meta = _to_plain_dict(payload.get("metadata"))
    return {
        "student_id": normalize_text(meta.get("student_id") or legacy_meta.get("student_id"), default=""),
        "target_job": normalize_text(
            meta.get("target_job")
            or legacy_meta.get("primary_job_title")
            or legacy_meta.get("career_intention"),
            default="",
        ),
        "generated_at": _infer_generated_at(payload),
    }


def _build_sections_from_legacy(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    grouped_blocks: dict[str, list[str]] = {key: [] for key in REPORT_SECTION_KEYS}

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
        content = _compose_section_content(raw_section)
        if content:
            grouped_blocks.setdefault(standard_key, []).append(content)

    recommendations = payload.get("recommendations") or []
    if recommendations and not grouped_blocks["match"]:
        recommendation_lines: list[str] = []
        for item in recommendations:
             if not isinstance(item, Mapping):
                  continue
             job_title = normalize_text(item.get("job_title"), default="未知岗位")
             reason = normalize_text(item.get("recommendation_reason"), default="")
             recommendation_lines.append(f"{job_title}：{reason}")

        grouped_blocks["match"].append(render_bullet_block(recommendation_lines))

    suggested_actions = render_action_block(payload.get("suggested_actions"))
    if suggested_actions and not grouped_blocks["plan_short"]:
        grouped_blocks["plan_short"].append(suggested_actions)

    return [
        {
            "key": key,
            "title": SECTION_TITLES[key],
            "content": join_content_blocks(*grouped_blocks.get(key, [])),
        }
        for key in REPORT_SECTION_KEYS
    ]


def _convert_report_json_to_section_based(payload: Any) -> dict[str, Any]:
    plain_payload = _to_plain_dict(payload)
    if plain_payload:
        payload = plain_payload
    if not isinstance(payload, Mapping):
        return {
            "meta": {"student_id": "", "target_job": "", "generated_at": ""},
            "sections": [{"key": key, "title": title, "content": ""} for key, title in SECTION_TITLES.items()],
        }

    if "content" in payload and isinstance(payload.get("content"), Mapping):
        normalized = _convert_report_json_to_section_based(payload.get("content"))
        if not normalized["meta"]["generated_at"]:
            normalized["meta"]["generated_at"] = _infer_generated_at(payload)
        return normalized

    if "meta" in payload and "sections" in payload:
        meta = _normalize_meta(payload)
        meta_payload = _to_plain_dict(payload.get("meta"))
        meta.update(
            {
                "student_id": normalize_text(meta_payload.get("student_id"), default=meta["student_id"]),
                "target_job": normalize_text(meta_payload.get("target_job"), default=meta["target_job"]),
                "generated_at": normalize_text(meta_payload.get("generated_at"), default=meta["generated_at"]),
            }
        )
        sections = []
        for raw_section in payload.get("sections") or []:
            section_payload = _to_plain_dict(raw_section)
            if not section_payload:
                if not isinstance(raw_section, Mapping):
                    continue
                section_payload = dict(raw_section)
            key = normalize_text(section_payload.get("key") or section_payload.get("section_key"), default="")
            sections.append(
                {
                    "key": key,
                    "title": normalize_text(section_payload.get("title"), default=SECTION_TITLES.get(key, key)),
                    "content": _compose_section_content(section_payload),
                }
            )
        return {"meta": meta, "sections": sections}

    return {"meta": _normalize_meta(payload), "sections": _build_sections_from_legacy(payload)}


class ReportActionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_id: str
    title: str
    description: str = TEXT_DEFAULT
    timeline: str = TEXT_DEFAULT
    priority: str = "medium"
    success_metric: str = TEXT_DEFAULT
    related_gap: str = TEXT_DEFAULT

    @field_validator(
        "action_id",
        "title",
        "description",
        "timeline",
        "priority",
        "success_metric",
        "related_gap",
        mode="before",
    )
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value)


class CareerPathOption(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path_label: str
    nodes: list[str] = Field(default_factory=list)
    rationale: str = TEXT_DEFAULT
    source_job_id: int | None = None

    @field_validator("path_label", "rationale", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator("nodes", mode="before")
    @classmethod
    def validate_nodes(cls, value: Any) -> list[str]:
        return normalize_list(value)


class CareerRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: int | None = None
    job_id: int
    job_profile_id: int
    job_title: str
    category: str = "match"
    total_score: float = 0.0
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    recommendation_reason: str = TEXT_DEFAULT
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    gap_analysis: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    key_actions: list[ReportActionItem] = Field(default_factory=list)
    career_paths: list[CareerPathOption] = Field(default_factory=list)

    @field_validator("job_title", "category", "recommendation_reason", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator("matched_skills", "missing_skills", "gap_analysis", "risk_flags", "evidence", mode="before")
    @classmethod
    def validate_lists(cls, value: Any) -> list[str]:
        return normalize_list(value)

    @field_validator("total_score", mode="before")
    @classmethod
    def validate_score(cls, value: Any) -> float:
        return clamp_score(value)


class CareerReportMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: str = TEXT_DEFAULT
    target_job: str = TEXT_DEFAULT
    generated_at: str = ""

    @field_validator("student_id", "target_job", "generated_at", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")


class CareerReportMetaUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: str | None = None
    target_job: str | None = None
    generated_at: str | None = None

    @field_validator("student_id", "target_job", "generated_at", mode="before")
    @classmethod
    def validate_optional_texts(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value, default="")
        return normalized or None


class CareerReportSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    title: str
    content: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        payload = dict(values)
        if not payload.get("key") and payload.get("section_key"):
            payload["key"] = payload.get("section_key")
        if payload.get("content") is None:
            payload["content"] = _compose_section_content(payload)
        return payload

    @field_validator("key", "title", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: Any) -> str:
        return normalize_report_multiline_text(value, default="")


class CareerReportContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    meta: CareerReportMeta
    sections: list[CareerReportSection] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, values: Any) -> Any:
        return _convert_report_json_to_section_based(values)


class ReportCompletenessItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    passed: bool
    message: str = TEXT_DEFAULT

    @field_validator("key", "message", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value)


class ReportCompletenessCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    score: float = 0.0
    is_complete: bool = False
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[ReportCompletenessItem] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def validate_score(cls, value: Any) -> float:
        return clamp_score(value)

    @field_validator("missing_sections", "warnings", mode="before")
    @classmethod
    def validate_lists(cls, value: Any) -> list[str]:
        return normalize_list(value)


class ReportEditorSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section_key: str
    title: str
    content: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        payload = dict(values)
        if not payload.get("section_key") and payload.get("key"):
            payload["section_key"] = payload.get("key")
        if payload.get("content") is None:
            payload["content"] = _compose_section_content(payload)
        return payload

    @field_validator("section_key", "title", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: Any) -> str:
        return normalize_report_multiline_text(value, default="")


class ReportEditorState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_title: str = "职业发展报告"
    sections: list[ReportEditorSection] = Field(default_factory=list)
    supported_export_formats: list[str] = Field(default_factory=lambda: list(SUPPORTED_EXPORT_FORMATS))

    @field_validator("report_title", mode="before")
    @classmethod
    def validate_title(cls, value: Any) -> str:
        return normalize_text(value, default="职业发展报告")


class CareerReportDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_id: int
    student_profile_id: int
    report_version: int
    report_title: str
    status: str
    primary_match_result_id: int | None = None
    primary_job_profile_id: int | None = None
    primary_job_id: int | None = None
    source_match_result_ids: list[int] = Field(default_factory=list)
    content: CareerReportContent
    recommendations: list[CareerRecommendation] = Field(default_factory=list)
    suggested_actions: list[ReportActionItem] = Field(default_factory=list)
    editor_state: ReportEditorState
    completeness_check: ReportCompletenessCheck
    markdown_content: str = ""
    html_content: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("report_title", "status", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("markdown_content", "html_content", mode="before")
    @classmethod
    def validate_document_content(cls, value: Any) -> str:
        return normalize_report_multiline_text(value, default="")


class CareerReportGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_profile_id: int
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=10)
    primary_job_id: int | None = None
    report_title: str | None = None
    persist: bool = True
    persist_matches: bool = True
    weights: MatchingWeights = Field(default_factory=MatchingWeights)

    @field_validator("report_title", mode="before")
    @classmethod
    def validate_title(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value, default="")
        return normalized or None


class CareerReportSectionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section_key: str
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    body_markdown: str | None = None
    bullets: list[str] | None = None
    action_items: list[ReportActionItem] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        payload = dict(values)
        if payload.get("content") is None:
            raw_actions = payload.get("action_items") or []
            action_items = [item.model_dump(mode="json") if isinstance(item, ReportActionItem) else item for item in raw_actions]
            payload["content"] = join_content_blocks(
                normalize_text(payload.get("body_markdown"), default="") or normalize_text(payload.get("summary"), default=""),
                render_bullet_block(payload.get("bullets")),
                render_action_block(action_items),
            )
        return payload

    @field_validator("section_key", "title", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value, default="")
        return normalized or None

    @field_validator("content", "summary", "body_markdown", mode="before")
    @classmethod
    def validate_multiline_texts(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_report_multiline_text(value, default="")
        return normalized or None

    @field_validator("bullets", mode="before")
    @classmethod
    def validate_bullets(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        return normalize_list(value)

    @model_validator(mode="after")
    def validate_has_update(self) -> "CareerReportSectionUpdate":
        if self.title is None and self.content is None:
            raise ValueError("At least one section field must be provided")
        return self


class CareerReportSectionPutRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    content: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value, default="")
        return normalized or None

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_report_multiline_text(value, default="")
        return normalized or None

    @model_validator(mode="after")
    def validate_has_update(self) -> "CareerReportSectionPutRequest":
        if self.title is None and self.content is None:
            raise ValueError("At least one section field must be provided")
        return self


class CareerReportUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_title: str | None = None
    status: str | None = None
    section_updates: list[CareerReportSectionUpdate] = Field(default_factory=list)

    @field_validator("report_title", "status", mode="before")
    @classmethod
    def validate_optional_texts(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value, default="")
        return normalized or None

    @model_validator(mode="after")
    def validate_has_update(self) -> "CareerReportUpdateRequest":
        if self.report_title is None and self.status is None and not self.section_updates:
            raise ValueError("At least one update field must be provided")
        return self


class CareerReportPutRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_title: str | None = None
    status: str | None = None
    meta: CareerReportMetaUpdate | None = None
    sections: list[CareerReportSectionUpdate] = Field(default_factory=list)

    @field_validator("report_title", "status", mode="before")
    @classmethod
    def validate_optional_texts(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value, default="")
        return normalized or None

    @model_validator(mode="after")
    def validate_has_update(self) -> "CareerReportPutRequest":
        if self.report_title is None and self.status is None and self.meta is None and not self.sections:
            raise ValueError("At least one update field must be provided")
        return self


class CareerReportExportPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    format: Literal["markdown", "html", "json", "pdf"]
    filename: str
    media_type: str
    content: str | bytes | dict[str, Any]
    output_path: str | None = None


class CareerReportSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_id: int
    student_profile_id: int
    report_version: int
    report_title: str
    status: str
    primary_job_title: str = TEXT_DEFAULT
    completeness_score: float = 0.0
    updated_at: datetime | None = None

    @field_validator("report_title", "status", "primary_job_title", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator("completeness_score", mode="before")
    @classmethod
    def validate_score(cls, value: Any) -> float:
        return clamp_score(value)


class CareerReportListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[CareerReportSummary] = Field(default_factory=list)
