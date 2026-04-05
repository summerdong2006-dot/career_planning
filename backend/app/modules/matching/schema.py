from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.matching.config import DEFAULT_MATCHING_WEIGHTS, DEFAULT_TOP_K, TEXT_DEFAULT
from app.modules.matching.utils import clamp_score, normalize_evidence_map, normalize_list, normalize_text


class MatchingWeights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_requirement: float = DEFAULT_MATCHING_WEIGHTS["base_requirement"]
    skill: float = DEFAULT_MATCHING_WEIGHTS["skill"]
    soft_skill: float = DEFAULT_MATCHING_WEIGHTS["soft_skill"]
    growth: float = DEFAULT_MATCHING_WEIGHTS["growth"]

    @field_validator("base_requirement", "skill", "soft_skill", "growth", mode="before")
    @classmethod
    def validate_weight(cls, value: Any) -> float:
        try:
            weight = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, round(weight, 4))

    def normalized(self) -> dict[str, float]:
        payload = self.model_dump()
        total = sum(payload.values()) or 1.0
        return {key: round(value / total, 6) for key, value in payload.items()}


class StudentMatchProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_profile_id: int
    student_id: str = TEXT_DEFAULT
    major: str = TEXT_DEFAULT
    summary: str = TEXT_DEFAULT
    education: str = TEXT_DEFAULT
    career_intention: str = TEXT_DEFAULT
    professional_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    innovation_score: float = 0.0
    learning_score: float = 0.0
    stress_score: float = 0.0
    communication_score: float = 0.0
    internship_score: float = 0.0
    professional_skill_score: float = 0.0
    completeness_score: float = 0.0
    competitiveness_score: float = 0.0
    internship_count: int = 0
    project_count: int = 0
    extracted_evidence: dict[str, list[str]] = Field(default_factory=dict)
    missing_items: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("student_id", "major", "summary", "education", "career_intention", mode="before")
    @classmethod
    def validate_text_fields(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator("professional_skills", "certificates", mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)

    @field_validator(
        "innovation_score",
        "learning_score",
        "stress_score",
        "communication_score",
        "internship_score",
        "professional_skill_score",
        "completeness_score",
        "competitiveness_score",
        mode="before",
    )
    @classmethod
    def validate_scores(cls, value: Any) -> float:
        return clamp_score(value)

    @field_validator("internship_count", "project_count", mode="before")
    @classmethod
    def validate_counts(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, parsed)

    @field_validator("extracted_evidence", mode="before")
    @classmethod
    def validate_evidence(cls, value: Any) -> dict[str, list[str]]:
        return normalize_evidence_map(value)


class JobMatchProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_profile_id: int
    job_id: int
    job_title: str = TEXT_DEFAULT
    job_level: str = TEXT_DEFAULT
    education_requirement: str = TEXT_DEFAULT
    years_experience_requirement: str = TEXT_DEFAULT
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    internship_requirement: str = TEXT_DEFAULT
    growth_potential: str = TEXT_DEFAULT
    promotion_path: list[str] = Field(default_factory=list)
    summary: str = TEXT_DEFAULT
    industry_tags: list[str] = Field(default_factory=list)
    extracted_evidence: dict[str, list[str]] = Field(default_factory=dict)
    confidence_score: float = 0.0

    @field_validator(
        "job_title",
        "job_level",
        "education_requirement",
        "years_experience_requirement",
        "internship_requirement",
        "growth_potential",
        "summary",
        mode="before",
    )
    @classmethod
    def validate_text_fields(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator(
        "must_have_skills",
        "nice_to_have_skills",
        "certificates",
        "soft_skills",
        "promotion_path",
        "industry_tags",
        mode="before",
    )
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def validate_confidence(cls, value: Any) -> float:
        return clamp_score(float(value) * 100 if isinstance(value, float) and value <= 1 else value)

    @field_validator("extracted_evidence", mode="before")
    @classmethod
    def validate_evidence(cls, value: Any) -> dict[str, list[str]]:
        return normalize_evidence_map(value)


class MatchDimensionScores(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_requirement: float = 0.0
    skill: float = 0.0
    soft_skill: float = 0.0
    growth: float = 0.0

    @field_validator("base_requirement", "skill", "soft_skill", "growth", mode="before")
    @classmethod
    def validate_scores(cls, value: Any) -> float:
        return clamp_score(value)


class MatchDimensionDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    score: float = 0.0
    matched: bool = False
    explanation: str = TEXT_DEFAULT
    evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unmet_items: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("score", mode="before")
    @classmethod
    def validate_score(cls, value: Any) -> float:
        return clamp_score(value)

    @field_validator("explanation", mode="before")
    @classmethod
    def validate_explanation(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator("evidence", "gaps", "unmet_items", mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)


class JobRequirementSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    must_have_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    innovation_requirement: float = 0.0
    learning_requirement: float = 0.0
    stress_tolerance_requirement: float = 0.0
    communication_requirement: float = 0.0
    internship_requirement: float = 0.0
    promotion_path: list[str] = Field(default_factory=list)

    @field_validator("must_have_skills", "certificates", "promotion_path", mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)

    @field_validator(
        "innovation_requirement",
        "learning_requirement",
        "stress_tolerance_requirement",
        "communication_requirement",
        "internship_requirement",
        mode="before",
    )
    @classmethod
    def validate_scores(cls, value: Any) -> float:
        return clamp_score(value)


class StudentCapabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    professional_skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    innovation_score: float = 0.0
    learning_score: float = 0.0
    stress_tolerance_score: float = 0.0
    communication_score: float = 0.0
    internship_score: float = 0.0
    completeness_score: float = 0.0
    competitiveness_score: float = 0.0

    @field_validator("professional_skills", "certificates", mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)

    @field_validator(
        "innovation_score",
        "learning_score",
        "stress_tolerance_score",
        "communication_score",
        "internship_score",
        "completeness_score",
        "competitiveness_score",
        mode="before",
    )
    @classmethod
    def validate_scores(cls, value: Any) -> float:
        return clamp_score(value)


class JobMatchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: int | None = None
    job_id: int
    job_profile_id: int
    job_title: str
    total_score: float
    dimension_scores: MatchDimensionScores
    matched: bool
    reason: str
    gap_analysis: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    dimension_details: dict[str, MatchDimensionDetail] = Field(default_factory=dict)
    job_requirement_snapshot: JobRequirementSnapshot = Field(default_factory=JobRequirementSnapshot)
    student_capability_snapshot: StudentCapabilitySnapshot = Field(default_factory=StudentCapabilitySnapshot)
    weight_config: MatchingWeights = Field(default_factory=MatchingWeights)
    created_at: datetime | None = None

    @field_validator("job_title", "reason", mode="before")
    @classmethod
    def validate_text_fields(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator("total_score", mode="before")
    @classmethod
    def validate_total_score(cls, value: Any) -> float:
        return clamp_score(value)

    @field_validator("gap_analysis", "evidence", "risk_flags", mode="before")
    @classmethod
    def validate_list_fields(cls, value: Any) -> list[str]:
        return normalize_list(value)


class MatchingRecommendRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_profile_id: int
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=50)
    persist: bool = True
    weights: MatchingWeights = Field(default_factory=MatchingWeights)


class MatchingRecommendResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_profile_id: int
    top_k: int
    matches: list[JobMatchResult] = Field(default_factory=list)


class MatchingBatchRecommendRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_profile_ids: list[int] = Field(default_factory=list)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=50)
    persist: bool = True
    weights: MatchingWeights = Field(default_factory=MatchingWeights)

    @model_validator(mode="after")
    def validate_items(self) -> "MatchingBatchRecommendRequest":
        if not self.student_profile_ids:
            raise ValueError("student_profile_ids must not be empty")
        return self


class MatchingBatchRecommendResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[MatchingRecommendResponse] = Field(default_factory=list)


class MatchDetailResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: int
    student_profile_id: int
    result: JobMatchResult

