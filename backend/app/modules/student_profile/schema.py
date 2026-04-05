from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TEXT_DEFAULT = "未明确"

TEXT_FIELDS = {
    "student_name",
    "student_no",
    "school",
    "major",
    "education",
    "grade",
    "career_intention",
    "summary",
    "resume_source",
}

LIST_FIELDS = {
    "skills",
    "certificates",
    "innovation_experiences",
}

ABILITY_FIELDS = {
    "professional_skills",
    "innovation",
    "learning",
    "stress_tolerance",
    "communication",
    "internship_ability",
}

ABILITY_LABELS = {
    "professional_skills": "专业技能",
    "innovation": "创新能力",
    "learning": "学习能力",
    "stress_tolerance": "抗压能力",
    "communication": "沟通能力",
    "internship_ability": "实习能力",
}

EVIDENCE_FIELDS = {
    "student_name",
    "student_no",
    "school",
    "major",
    "education",
    "grade",
    "skills",
    "projects",
    "internships",
    "competitions",
    "certificates",
    "student_work",
    "career_intention",
    "professional_skills",
    "innovation",
    "learning",
    "stress_tolerance",
    "communication",
    "internship_ability",
    "completeness_score",
    "competitiveness_score",
    "missing_items",
    "summary",
}


def normalize_text_field(value: Any, default: str = TEXT_DEFAULT) -> str:
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
    text = str(value).replace("\u3000", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else default


def normalize_multiline_text_field(value: Any, default: str = TEXT_DEFAULT) -> str:
    if value is None:
        return default
    if isinstance(value, list):
        for item in value:
            text = normalize_multiline_text_field(item, default="")
            if text:
                return text
        return default
    if isinstance(value, dict):
        return default
    text = str(value).replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text if text else default


def normalize_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        return []
    raw_items = value if isinstance(value, list) else re.split(r"[\n,，/、;；|]+", str(value))
    result: list[str] = []
    for item in raw_items:
        text = normalize_text_field(item, default="")
        if text and text not in result:
            result.append(text)
    return result


def normalize_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, round(score, 2)))


class StudentProfileAbilityScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    professional_skills: float = 0.0
    innovation: float = 0.0
    learning: float = 0.0
    stress_tolerance: float = 0.0
    communication: float = 0.0
    internship_ability: float = 0.0

    @field_validator(*ABILITY_FIELDS, mode="before")
    @classmethod
    def validate_scores(cls, value: Any) -> float:
        return normalize_score(value)


class StudentProfileEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_name: list[str] = Field(default_factory=list)
    student_no: list[str] = Field(default_factory=list)
    school: list[str] = Field(default_factory=list)
    major: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    grade: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    internships: list[str] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    student_work: list[str] = Field(default_factory=list)
    career_intention: list[str] = Field(default_factory=list)
    professional_skills: list[str] = Field(default_factory=list)
    innovation: list[str] = Field(default_factory=list)
    learning: list[str] = Field(default_factory=list)
    stress_tolerance: list[str] = Field(default_factory=list)
    communication: list[str] = Field(default_factory=list)
    internship_ability: list[str] = Field(default_factory=list)
    completeness_score: list[str] = Field(default_factory=list)
    competitiveness_score: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)

    @field_validator(*EVIDENCE_FIELDS, mode="before")
    @classmethod
    def validate_evidence_lists(cls, value: Any) -> list[str]:
        return normalize_list_field(value)


class StudentProject(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = TEXT_DEFAULT
    role: str = TEXT_DEFAULT
    description: str = TEXT_DEFAULT

    @field_validator("name", "role", "description", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text_field(value)


class StudentInternship(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = TEXT_DEFAULT
    role: str = TEXT_DEFAULT
    description: str = TEXT_DEFAULT

    @field_validator("company", "role", "description", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text_field(value)


class StudentCompetition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = TEXT_DEFAULT
    award: str = TEXT_DEFAULT
    description: str = TEXT_DEFAULT

    @field_validator("name", "award", "description", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text_field(value)


class StudentWorkExperience(BaseModel):
    model_config = ConfigDict(extra="ignore")

    organization: str = TEXT_DEFAULT
    role: str = TEXT_DEFAULT
    description: str = TEXT_DEFAULT

    @field_validator("organization", "role", "description", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text_field(value)


class MissingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str
    label: str
    suggestion: str
    severity: str = "medium"

    @field_validator("field", "label", "suggestion", "severity", mode="before")
    @classmethod
    def validate_texts(cls, value: Any) -> str:
        return normalize_text_field(value)


class ScoringWeights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    professional_skills: float = 0.24
    innovation: float = 0.16
    learning: float = 0.16
    stress_tolerance: float = 0.12
    communication: float = 0.14
    internship_ability: float = 0.18

    @field_validator(*ABILITY_FIELDS, mode="before")
    @classmethod
    def validate_weight(cls, value: Any) -> float:
        try:
            weight = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, round(weight, 4))

    def normalized(self) -> dict[str, float]:
        weights = self.model_dump()
        total = sum(weights.values()) or 1.0
        return {key: value / total for key, value in weights.items()}


class StudentProfilePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_name: str = TEXT_DEFAULT
    student_no: str = TEXT_DEFAULT
    school: str = TEXT_DEFAULT
    major: str = TEXT_DEFAULT
    education: str = TEXT_DEFAULT
    grade: str = TEXT_DEFAULT
    skills: list[str] = Field(default_factory=list)
    projects: list[StudentProject] = Field(default_factory=list)
    internships: list[StudentInternship] = Field(default_factory=list)
    competitions: list[StudentCompetition] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    student_work: list[StudentWorkExperience] = Field(default_factory=list)
    career_intention: str = TEXT_DEFAULT
    innovation_experiences: list[str] = Field(default_factory=list)
    ability_scores: StudentProfileAbilityScore = Field(default_factory=StudentProfileAbilityScore)
    completeness_score: float = 0.0
    competitiveness_score: float = 0.0
    missing_items: list[MissingItem] = Field(default_factory=list)
    evidence: StudentProfileEvidence = Field(default_factory=StudentProfileEvidence)
    summary: str = TEXT_DEFAULT
    resume_source: str = TEXT_DEFAULT

    @field_validator(*TEXT_FIELDS, mode="before")
    @classmethod
    def validate_text_fields(cls, value: Any) -> str:
        return normalize_text_field(value)

    @field_validator(*LIST_FIELDS, mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list_field(value)

    @field_validator("completeness_score", "competitiveness_score", mode="before")
    @classmethod
    def validate_score_fields(cls, value: Any) -> float:
        return normalize_score(value)


class StudentProfileSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: str
    resume_text: str = TEXT_DEFAULT
    manual_form: dict[str, Any] = Field(default_factory=dict)
    supplement_text: str = TEXT_DEFAULT
    basic_info: dict[str, Any] = Field(default_factory=dict)
    resume_filename: str = TEXT_DEFAULT

    @field_validator("student_id", mode="before")
    @classmethod
    def validate_student_id(cls, value: Any) -> str:
        return normalize_text_field(value, default="")

    @field_validator("resume_text", "supplement_text", mode="before")
    @classmethod
    def validate_multiline_text_inputs(cls, value: Any) -> str:
        return normalize_multiline_text_field(value)

    @field_validator("resume_filename", mode="before")
    @classmethod
    def validate_filename_input(cls, value: Any) -> str:
        return normalize_text_field(value)

    @field_validator("manual_form", "basic_info", mode="before")
    @classmethod
    def validate_json_objects(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @model_validator(mode="after")
    def validate_has_content(self) -> "StudentProfileSource":
        has_resume = self.resume_text != TEXT_DEFAULT
        has_manual = bool(self.manual_form)
        has_supplement = self.supplement_text != TEXT_DEFAULT
        if not (has_resume or has_manual or has_supplement):
            raise ValueError("At least one of resume_text, manual_form or supplement_text must be provided")
        if not self.student_id:
            raise ValueError("student_id is required")
        return self


class StudentProfileRecordRef(BaseModel):
    profile_id: int | None = None
    resume_id: int | None = None


class StudentProfileBuildResult(BaseModel):
    student_id: str
    profile_version: int
    persisted: bool
    profile: StudentProfilePayload
    raw_profile_payload: dict[str, Any] = Field(default_factory=dict)
    record_refs: StudentProfileRecordRef = Field(default_factory=StudentProfileRecordRef)
    created_at: datetime | None = None


class StudentProfileBuildRequest(BaseModel):
    source: StudentProfileSource
    persist: bool = True
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)


class StudentProfileUpdateRequest(BaseModel):
    resume_text: str | None = None
    manual_form: dict[str, Any] | None = None
    supplement_text: str | None = None
    basic_info: dict[str, Any] | None = None
    resume_filename: str | None = None
    persist: bool = True
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)

    @model_validator(mode="after")
    def validate_has_updates(self) -> "StudentProfileUpdateRequest":
        if not any(
            value is not None
            for value in (
                self.resume_text,
                self.manual_form,
                self.supplement_text,
                self.basic_info,
                self.resume_filename,
            )
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class StudentProfileBatchRequest(BaseModel):
    items: list[StudentProfileSource] = Field(default_factory=list)
    persist: bool = True
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)

    @model_validator(mode="after")
    def validate_items(self) -> "StudentProfileBatchRequest":
        if not self.items:
            raise ValueError("items must not be empty")
        return self


class StudentProfileBatchResponse(BaseModel):
    requested_records: int
    processed_records: int
    persisted_records: int
    failed_records: int
    items: list[StudentProfileBuildResult] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)


class StudentProfileExportResponse(BaseModel):
    student_id: str
    version: int
    payload: dict[str, Any] = Field(default_factory=dict)
