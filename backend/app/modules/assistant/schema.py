from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AssistantRole = Literal["user", "assistant"]


class AssistantMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: AssistantRole
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content cannot be empty")
        return normalized


class AssistantPageContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page_name: str = Field(min_length=1, max_length=64)
    page_label: str | None = Field(default=None, max_length=128)
    student_profile_id: int | None = None
    report_id: int | None = None
    resume_id: int | None = None
    notes: str | None = Field(default=None, max_length=1200)

    @field_validator("page_name")
    @classmethod
    def validate_page_name(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("page_label", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: list[AssistantMessage] = Field(min_length=1, max_length=20)
    context: AssistantPageContext | None = None

    @model_validator(mode="after")
    def validate_last_message(self) -> "AssistantChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("last message must be from user")
        return self


class AssistantChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reply: str
    provider: str
    model: str
    used_context: bool = False
