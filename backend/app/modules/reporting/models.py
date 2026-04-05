from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CareerReportRecord(Base):
    __tablename__ = "career_reports"
    __table_args__ = (
        UniqueConstraint("student_profile_id", "report_version", name="uq_career_report_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), nullable=False, index=True)
    primary_match_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("match_results.id"),
        nullable=True,
        index=True,
    )
    primary_job_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_posting_profiles.id"),
        nullable=True,
        index=True,
    )
    primary_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    report_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    report_title: Mapped[str] = mapped_column(String(255), nullable=False, default="职业发展报告")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    source_match_result_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    generation_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    report_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    editor_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    completeness_check: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    html_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
