from __future__ import annotations

import hashlib
import secrets
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import get_db_session
from app.modules.auth.models import (
    UserAccount,
    UserCareerReportLink,
    UserGeneratedResumeLink,
    UserSessionRecord,
    UserStudentProfileLink,
)
from app.modules.auth.schema import (
    AuthSessionResponse,
    AuthUser,
    ReportWorkspaceSummary,
    ResumeWorkspaceSummary,
    StudentWorkspaceSummary,
    WorkspaceOverviewResponse,
)
from app.modules.reporting.models import CareerReportRecord
from app.modules.student_profile.models import ResumeRecord, StudentProfileRecord

security = HTTPBearer(auto_error=False)


async def ensure_auth_tables(session: AsyncSession) -> None:
    async with session.bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def _hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return derived.hex()


def _build_auth_user(record: UserAccount) -> AuthUser:
    return AuthUser(
        id=record.id,
        email=record.email,
        display_name=record.display_name,
        created_at=record.created_at,
    )


async def _create_session_for_user(session: AsyncSession, user: UserAccount) -> AuthSessionResponse:
    token = secrets.token_urlsafe(32)
    session_record = UserSessionRecord(user_id=user.id, session_token=token)
    session.add(session_record)
    await session.flush()
    return AuthSessionResponse(token=token, user=_build_auth_user(user))


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    display_name: str,
    password: str,
) -> AuthSessionResponse:
    await ensure_auth_tables(session)
    existing = await session.execute(select(UserAccount).where(UserAccount.email == email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise AppException(message="该邮箱已注册", error_code="auth_email_exists", status_code=409)

    salt = secrets.token_hex(16)
    user = UserAccount(
        email=email.lower(),
        display_name=display_name.strip(),
        password_hash=_hash_password(password, salt),
        password_salt=salt,
    )
    session.add(user)
    await session.flush()
    auth = await _create_session_for_user(session, user)
    await session.commit()
    return auth


async def login_user(session: AsyncSession, *, email: str, password: str) -> AuthSessionResponse:
    await ensure_auth_tables(session)
    result = await session.execute(select(UserAccount).where(UserAccount.email == email.lower()))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash != _hash_password(password, user.password_salt):
        raise AppException(message="邮箱或密码错误", error_code="auth_invalid_credentials", status_code=401)

    auth = await _create_session_for_user(session, user)
    await session.commit()
    return auth


async def logout_user(session: AsyncSession, *, token: str) -> None:
    await ensure_auth_tables(session)
    await session.execute(delete(UserSessionRecord).where(UserSessionRecord.session_token == token))
    await session.commit()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> UserAccount:
    await ensure_auth_tables(session)
    token = credentials.credentials if credentials else None
    if not token:
        raise AppException(message="请先登录", error_code="auth_required", status_code=401)

    result = await session.execute(
        select(UserAccount)
        .join(UserSessionRecord, UserSessionRecord.user_id == UserAccount.id)
        .where(UserSessionRecord.session_token == token)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AppException(message="登录状态已失效，请重新登录", error_code="auth_invalid_session", status_code=401)
    return user


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    token = credentials.credentials if credentials else None
    if not token:
        raise AppException(message="请先登录", error_code="auth_required", status_code=401)
    return token


async def link_student_profile_to_user(session: AsyncSession, *, user_id: int, student_profile_id: int) -> None:
    await ensure_auth_tables(session)
    existing = await session.execute(
        select(UserStudentProfileLink).where(UserStudentProfileLink.student_profile_id == student_profile_id)
    )
    if existing.scalar_one_or_none() is None:
        session.add(UserStudentProfileLink(user_id=user_id, student_profile_id=student_profile_id))
        await session.commit()


async def link_report_to_user(session: AsyncSession, *, user_id: int, report_id: int) -> None:
    await ensure_auth_tables(session)
    existing = await session.execute(select(UserCareerReportLink).where(UserCareerReportLink.report_id == report_id))
    if existing.scalar_one_or_none() is None:
        session.add(UserCareerReportLink(user_id=user_id, report_id=report_id))
        await session.commit()


async def link_resume_to_user(session: AsyncSession, *, user_id: int, resume_id: int) -> None:
    await ensure_auth_tables(session)
    existing = await session.execute(
        select(UserGeneratedResumeLink).where(UserGeneratedResumeLink.resume_id == resume_id)
    )
    if existing.scalar_one_or_none() is None:
        session.add(UserGeneratedResumeLink(user_id=user_id, resume_id=resume_id))
        await session.commit()


async def assert_student_profile_access(session: AsyncSession, *, user_id: int, student_profile_id: int) -> None:
    await ensure_auth_tables(session)
    result = await session.execute(
        select(UserStudentProfileLink).where(
            UserStudentProfileLink.user_id == user_id,
            UserStudentProfileLink.student_profile_id == student_profile_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise AppException(message="无权访问该学生画像", error_code="student_profile_forbidden", status_code=403)


async def assert_report_access(session: AsyncSession, *, user_id: int, report_id: int) -> None:
    await ensure_auth_tables(session)
    result = await session.execute(
        select(UserCareerReportLink).where(
            UserCareerReportLink.user_id == user_id,
            UserCareerReportLink.report_id == report_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise AppException(message="无权访问该职业报告", error_code="career_report_forbidden", status_code=403)


async def assert_resume_access(session: AsyncSession, *, user_id: int, resume_id: int) -> None:
    await ensure_auth_tables(session)
    result = await session.execute(
        select(UserGeneratedResumeLink).where(
            UserGeneratedResumeLink.user_id == user_id,
            UserGeneratedResumeLink.resume_id == resume_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise AppException(message="无权访问该简历", error_code="resume_forbidden", status_code=403)


async def get_owned_student_profile(
    session: AsyncSession,
    *,
    user_id: int,
    student_id: str,
    version: int | None = None,
) -> StudentProfileRecord:
    await ensure_auth_tables(session)
    query = (
        select(StudentProfileRecord)
        .join(UserStudentProfileLink, UserStudentProfileLink.student_profile_id == StudentProfileRecord.id)
        .where(UserStudentProfileLink.user_id == user_id, StudentProfileRecord.student_id == student_id)
    )
    if version is not None:
        query = query.where(StudentProfileRecord.profile_version == version)
    else:
        query = query.order_by(desc(StudentProfileRecord.profile_version), desc(StudentProfileRecord.id)).limit(1)
    record = (await session.execute(query)).scalar_one_or_none()
    if record is None:
        raise AppException(message="未找到属于当前账号的学生画像", error_code="student_profile_not_found", status_code=404)
    return record


async def build_workspace_overview(session: AsyncSession, *, user: UserAccount) -> WorkspaceOverviewResponse:
    await ensure_auth_tables(session)

    profile_rows = (
        await session.execute(
            select(StudentProfileRecord)
            .join(UserStudentProfileLink, UserStudentProfileLink.student_profile_id == StudentProfileRecord.id)
            .where(UserStudentProfileLink.user_id == user.id)
            .order_by(desc(StudentProfileRecord.updated_at), desc(StudentProfileRecord.id))
            .limit(12)
        )
    ).scalars().all()

    report_rows = (
        await session.execute(
            select(CareerReportRecord)
            .join(UserCareerReportLink, UserCareerReportLink.report_id == CareerReportRecord.id)
            .where(UserCareerReportLink.user_id == user.id)
            .order_by(desc(CareerReportRecord.updated_at), desc(CareerReportRecord.id))
            .limit(12)
        )
    ).scalars().all()

    resume_rows = (
        await session.execute(
            select(ResumeRecord)
            .join(UserGeneratedResumeLink, UserGeneratedResumeLink.resume_id == ResumeRecord.id)
            .where(UserGeneratedResumeLink.user_id == user.id)
            .order_by(desc(ResumeRecord.created_at), desc(ResumeRecord.id))
            .limit(12)
        )
    ).scalars().all()

    return WorkspaceOverviewResponse(
        user=_build_auth_user(user),
        student_profiles=[
            StudentWorkspaceSummary(
                profile_id=row.id,
                student_id=row.student_id,
                profile_version=row.profile_version,
                summary=row.summary,
                career_intention=row.career_intention,
                updated_at=row.updated_at,
            )
            for row in profile_rows
        ],
        reports=[
            ReportWorkspaceSummary(
                report_id=row.id,
                student_profile_id=row.student_profile_id,
                report_title=row.report_title,
                status=row.status,
                updated_at=row.updated_at,
            )
            for row in report_rows
        ],
        resumes=[
            ResumeWorkspaceSummary(
                resume_id=row.id,
                student_profile_id=(row.source_payload or {}).get("student_profile_id", 0),
                target_job=(row.source_payload or {}).get("target_job", ""),
                style=(row.source_payload or {}).get("style", ""),
                created_at=row.created_at,
            )
            for row in resume_rows
        ],
    )
