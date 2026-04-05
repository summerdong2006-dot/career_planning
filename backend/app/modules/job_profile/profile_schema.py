from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

JOB_PROFILE_FIELD_NAMES = [
    "job_title",
    "job_level",
    "education_requirement",
    "years_experience_requirement",
    "must_have_skills",
    "nice_to_have_skills",
    "certificates",
    "soft_skills",
    "internship_requirement",
    "industry_tags",
    "promotion_path",
    "summary",
    "extracted_evidence",
    "confidence_score",
]

EVIDENCE_FIELD_NAMES = [
    "job_title",
    "job_level",
    "education_requirement",
    "years_experience_requirement",
    "must_have_skills",
    "nice_to_have_skills",
    "certificates",
    "soft_skills",
    "internship_requirement",
    "industry_tags",
    "promotion_path",
    "summary",
]

TEXT_PROFILE_FIELDS = {
    "job_title",
    "job_level",
    "education_requirement",
    "years_experience_requirement",
    "internship_requirement",
    "summary",
}

LIST_PROFILE_FIELDS = {
    "must_have_skills",
    "nice_to_have_skills",
    "certificates",
    "soft_skills",
    "industry_tags",
    "promotion_path",
}


def normalize_text_field(value: Any, default: str = "未明确") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        for item in value:
            text = normalize_text_field(item, default="")
            if text:
                return text
        return default
    if isinstance(value, dict):
        return default
    text = " ".join(str(value).replace("\u3000", " ").split()).strip()
    if not text or text == "[]":
        return default
    return text


def normalize_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        return []
    if isinstance(value, list):
        values = value
    else:
        text = normalize_text_field(value, default="")
        if not text or text == "未明确":
            return []
        values = [segment for segment in re.split(r"[,，/、;；|]+", text) if segment]
    normalized: list[str] = []
    for item in values:
        text = normalize_text_field(item, default="")
        if text and text != "未明确" and text not in normalized:
            normalized.append(text)
    return normalized


class JobProfileEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_title: list[str] = Field(default_factory=list)
    job_level: list[str] = Field(default_factory=list)
    education_requirement: list[str] = Field(default_factory=list)
    years_experience_requirement: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    internship_requirement: list[str] = Field(default_factory=list)
    industry_tags: list[str] = Field(default_factory=list)
    promotion_path: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)

    @field_validator(*EVIDENCE_FIELD_NAMES, mode="before")
    @classmethod
    def normalize_evidence_list(cls, value: Any) -> list[str]:
        return normalize_list_field(value)


class JobProfilePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_title: str = "未明确"
    job_level: str = "未明确"
    education_requirement: str = "未明确"
    years_experience_requirement: str = "未明确"
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    internship_requirement: str = "未明确"
    industry_tags: list[str] = Field(default_factory=list)
    promotion_path: list[str] = Field(default_factory=list)
    summary: str = "未明确"
    extracted_evidence: JobProfileEvidence = Field(default_factory=JobProfileEvidence)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator(*TEXT_PROFILE_FIELDS, mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> str:
        return normalize_text_field(value)

    @field_validator(*LIST_PROFILE_FIELDS, mode="before")
    @classmethod
    def normalize_list_fields(cls, value: Any) -> list[str]:
        return normalize_list_field(value)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def normalize_confidence_score(cls, value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, score))


class JobProfileSourceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_clean_id: int | None = None
    batch_id: int | None = None
    canonical_key: str | None = None
    position_name: str
    position_name_normalized: str | None = None
    job_category: str = ""
    work_city: str = ""
    salary_range: str = ""
    company_full_name: str = ""
    industry: str = ""
    job_description: str = ""
    company_intro: str = ""
    job_tags: list[str] = Field(default_factory=list)


class SingleJobProfileExtractRequest(BaseModel):
    source_clean_id: int | None = None
    job_data: JobProfileSourceRecord | None = None
    persist: bool = True

    @model_validator(mode="after")
    def validate_input(self) -> "SingleJobProfileExtractRequest":
        if self.source_clean_id is None and self.job_data is None:
            raise ValueError("Either source_clean_id or job_data must be provided")
        return self


class JobProfileExtractionResult(BaseModel):
    source_clean_id: int | None = None
    batch_id: int | None = None
    extractor_name: str
    extractor_version: str
    persisted: bool
    profile: JobProfilePayload
    raw_profile_payload: dict[str, Any] = Field(default_factory=dict)


class BatchJobProfileExtractRequest(BaseModel):
    batch_id: int | None = None
    source_clean_ids: list[int] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=50)
    persist: bool = True

    @model_validator(mode="after")
    def validate_input(self) -> "BatchJobProfileExtractRequest":
        if self.batch_id is None and not self.source_clean_ids:
            raise ValueError("Either batch_id or source_clean_ids must be provided")
        return self


class BatchJobProfileExtractResponse(BaseModel):
    batch_id: int | None = None
    requested_records: int
    processed_records: int
    persisted_records: int
    failed_records: int
    limit: int
    items: list[JobProfileExtractionResult] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)
