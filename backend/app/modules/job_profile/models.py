from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobImportBatch(Base):
    __tablename__ = "job_import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_format: Mapped[str] = mapped_column(String(32), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
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
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobPostingRaw(Base):
    __tablename__ = "job_postings_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("job_import_batches.id"), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    position_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    work_address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    salary_range: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    company_full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    company_size: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    company_type: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    job_code: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    job_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    company_intro: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    clean_status: Mapped[str] = mapped_column(String(32), nullable=False, default="imported")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class JobPostingClean(Base):
    __tablename__ = "job_postings_clean"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("job_import_batches.id"), nullable=False, index=True)
    source_raw_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings_raw.id"),
        nullable=False,
        unique=True,
    )
    canonical_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    position_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position_name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    job_category: Mapped[str] = mapped_column(String(64), nullable=False)
    work_city: Mapped[str] = mapped_column(String(128), nullable=False)
    work_address: Mapped[str] = mapped_column(String(255), nullable=False)
    salary_range: Mapped[str] = mapped_column(String(255), nullable=False)
    salary_min_monthly: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max_monthly: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_pay_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    salary_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="monthly")
    company_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(255), nullable=False)
    company_size: Mapped[str] = mapped_column(String(64), nullable=False)
    company_type: Mapped[str] = mapped_column(String(64), nullable=False)
    job_code: Mapped[str] = mapped_column(String(255), nullable=False)
    job_code_generated: Mapped[bool] = mapped_column(nullable=False, default=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    company_intro: Mapped[str] = mapped_column(Text, nullable=False)
    job_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class JobCleaningLog(Base):
    __tablename__ = "job_cleaning_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("job_import_batches.id"), nullable=False, index=True)
    raw_id: Mapped[int | None] = mapped_column(ForeignKey("job_postings_raw.id"), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class JobPostingProfile(Base):
    __tablename__ = "job_posting_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("job_import_batches.id"), nullable=False, index=True)
    source_clean_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings_clean.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    job_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    job_level: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    education_requirement: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    years_experience_requirement: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    must_have_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    nice_to_have_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    certificates: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    soft_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    internship_requirement: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    industry_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    promotion_path: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extracted_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extractor_name: Mapped[str] = mapped_column(String(64), nullable=False, default="heuristic")
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
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


class JobProfileExtractionLog(Base):
    __tablename__ = "job_profile_extraction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("job_import_batches.id"), nullable=True, index=True)
    clean_id: Mapped[int | None] = mapped_column(ForeignKey("job_postings_clean.id"), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
