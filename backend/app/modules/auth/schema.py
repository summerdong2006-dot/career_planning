from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    email: str
    display_name: str
    created_at: datetime | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("invalid email")
        return normalized


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: str
    user: AuthUser


class AuthRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("invalid email")
        return normalized


class AuthLoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("invalid email")
        return normalized


class StudentWorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile_id: int
    student_id: str
    profile_version: int
    summary: str
    career_intention: str
    updated_at: datetime | None = None


class ReportWorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_id: int
    student_profile_id: int
    report_title: str
    status: str
    updated_at: datetime | None = None


class ResumeWorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resume_id: int
    student_profile_id: int
    target_job: str
    style: str
    created_at: datetime | None = None


class WorkspaceOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user: AuthUser
    student_profiles: list[StudentWorkspaceSummary]
    reports: list[ReportWorkspaceSummary]
    resumes: list[ResumeWorkspaceSummary]
