from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.matching.utils import normalize_list, normalize_text

RESUME_STYLE_OPTIONS = ("campus",)
RESUME_EXPORT_FORMATS = ("markdown", "html", "json")


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = normalize_text(value, default="")
    return normalized or None


class ResumeBasicInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_name: str = ""
    student_id: str = ""
    school: str = ""
    major: str = ""
    education: str = ""
    grade: str = ""

    @field_validator("student_name", "student_id", "school", "major", "education", "grade", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")


class ResumeJobIntention(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_job: str = ""
    target_city: str = ""
    style: str = "campus"

    @field_validator("target_job", "target_city", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("style", mode="before")
    @classmethod
    def validate_style(cls, value: Any) -> str:
        normalized = normalize_text(value, default="campus").lower()
        return normalized if normalized in RESUME_STYLE_OPTIONS else "campus"


class ResumeEducationEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    school: str = ""
    major: str = ""
    education: str = ""
    grade: str = ""
    highlights: list[str] = Field(default_factory=list)

    @field_validator("school", "major", "education", "grade", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("highlights", mode="before")
    @classmethod
    def validate_highlights(cls, value: Any) -> list[str]:
        return normalize_list(value)


class ResumeProjectEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    role: str = ""
    highlights: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)

    @field_validator("name", "role", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("highlights", "tech_stack", mode="before")
    @classmethod
    def validate_lists(cls, value: Any) -> list[str]:
        return normalize_list(value)


class ResumeInternshipEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = ""
    role: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)

    @field_validator("company", "role", "duration", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("highlights", mode="before")
    @classmethod
    def validate_highlights(cls, value: Any) -> list[str]:
        return normalize_list(value)


class ResumeContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    basic_info: ResumeBasicInfo = Field(default_factory=ResumeBasicInfo)
    job_intention: ResumeJobIntention = Field(default_factory=ResumeJobIntention)
    summary: str = ""
    education: list[ResumeEducationEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[ResumeProjectEntry] = Field(default_factory=list)
    internships: list[ResumeInternshipEntry] = Field(default_factory=list)
    extras: list[str] = Field(default_factory=list)

    @field_validator("summary", mode="before")
    @classmethod
    def validate_summary(cls, value: Any) -> str:
        return normalize_text(value, default="")

    @field_validator("skills", "extras", mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)


class ResumeGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_profile_id: int
    target_job: str
    style: str = "campus"
    persist: bool = True

    @field_validator("target_job", mode="before")
    @classmethod
    def validate_target_job(cls, value: Any) -> str:
        normalized = normalize_text(value, default="")
        if not normalized:
            raise ValueError("target_job is required")
        return normalized

    @field_validator("style", mode="before")
    @classmethod
    def validate_style(cls, value: Any) -> str:
        normalized = normalize_text(value, default="campus").lower()
        if normalized not in RESUME_STYLE_OPTIONS:
            raise ValueError(f"style must be one of: {', '.join(RESUME_STYLE_OPTIONS)}")
        return normalized


class ResumeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_job: str | None = None
    style: str | None = None
    basic_info: ResumeBasicInfo | None = None
    job_intention: ResumeJobIntention | None = None
    summary: str | None = None
    education: list[ResumeEducationEntry] | None = None
    skills: list[str] | None = None
    projects: list[ResumeProjectEntry] | None = None
    internships: list[ResumeInternshipEntry] | None = None
    extras: list[str] | None = None

    @field_validator("target_job", "summary", mode="before")
    @classmethod
    def validate_optional_texts(cls, value: Any) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("style", mode="before")
    @classmethod
    def validate_optional_style(cls, value: Any) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        lowered = normalized.lower()
        if lowered not in RESUME_STYLE_OPTIONS:
            raise ValueError(f"style must be one of: {', '.join(RESUME_STYLE_OPTIONS)}")
        return lowered

    @field_validator("skills", "extras", mode="before")
    @classmethod
    def validate_optional_lists(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        return normalize_list(value)

    @model_validator(mode="after")
    def validate_has_updates(self) -> "ResumeUpdateRequest":
        if not any(
            value is not None
            for value in (
                self.target_job,
                self.style,
                self.basic_info,
                self.job_intention,
                self.summary,
                self.education,
                self.skills,
                self.projects,
                self.internships,
                self.extras,
            )
        ):
            raise ValueError("At least one update field must be provided")
        return self


class ResumeExportPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    format: Literal["markdown", "html", "json"]
    filename: str
    media_type: str
    content: str | dict[str, Any]


class ResumeDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resume_id: int
    student_profile_id: int
    student_id: str
    target_job: str
    style: str
    content: ResumeContent
    markdown_content: str = ""
    html_content: str = ""
    created_at: datetime | None = None

    @field_validator("student_id", "target_job", "style", "markdown_content", "html_content", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")


class ResumeStoredPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: str = "generated_resume"
    student_profile_id: int
    student_id: str
    target_job: str
    style: str
    content: ResumeContent
    markdown_content: str = ""
    html_content: str = ""

    @field_validator("kind", "student_id", "target_job", "style", "markdown_content", "html_content", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text(value, default="")


class ResumeJsonResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resume_id: int
    student_profile_id: int
    student_id: str
    target_job: str
    style: str
    content: ResumeContent


def merge_model(base: BaseModel, update: BaseModel) -> BaseModel:
    payload = base.model_dump(mode="json")
    payload.update(update.model_dump(mode="json"))
    return type(base).model_validate(payload)


def merge_resume_content(content: ResumeContent, request: ResumeUpdateRequest) -> ResumeContent:
    payload = content.model_dump(mode="json")
    if request.basic_info is not None:
        payload["basic_info"] = request.basic_info.model_dump(mode="json")
    if request.job_intention is not None:
        payload["job_intention"] = request.job_intention.model_dump(mode="json")
    if request.summary is not None:
        payload["summary"] = request.summary
    if request.education is not None:
        payload["education"] = [item.model_dump(mode="json") for item in request.education]
    if request.skills is not None:
        payload["skills"] = request.skills
    if request.projects is not None:
        payload["projects"] = [item.model_dump(mode="json") for item in request.projects]
    if request.internships is not None:
        payload["internships"] = [item.model_dump(mode="json") for item in request.internships]
    if request.extras is not None:
        payload["extras"] = request.extras
    if request.target_job is not None:
        payload.setdefault("job_intention", {})["target_job"] = request.target_job
    if request.style is not None:
        payload.setdefault("job_intention", {})["style"] = request.style
    return ResumeContent.model_validate(payload)


def resume_detail_from_mapping(payload: Mapping[str, Any]) -> ResumeDetail:
    return ResumeDetail.model_validate(dict(payload))
