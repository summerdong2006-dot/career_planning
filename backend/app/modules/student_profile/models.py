from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResumeRecord(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    resume_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="未明确")
    resume_text: Mapped[str] = mapped_column(Text, nullable=False, default="未明确")
    manual_form_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    supplement_text: Mapped[str] = mapped_column(Text, nullable=False, default="未明确")
    basic_info_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class StudentProfileRecord(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint("student_id", "profile_version", name="uq_student_profile_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True, index=True)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="未明确")
    school: Mapped[str] = mapped_column(String(255), nullable=False, default="未明确")
    major: Mapped[str] = mapped_column(String(255), nullable=False, default="未明确")
    education: Mapped[str] = mapped_column(String(64), nullable=False, default="未明确")
    grade: Mapped[str] = mapped_column(String(64), nullable=False, default="未明确")
    career_intention: Mapped[str] = mapped_column(Text, nullable=False, default="未明确")
    resume_source: Mapped[str] = mapped_column(String(32), nullable=False, default="未明确")
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    competitiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ability_scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    extracted_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    missing_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    raw_profile_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class StudentProfileItemRecord(Base):
    __tablename__ = "student_profile_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(128), nullable=False)
    item_label: Mapped[str] = mapped_column(String(255), nullable=False, default="未明确")
    item_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
