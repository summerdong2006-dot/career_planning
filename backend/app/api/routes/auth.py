from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schema import AuthLoginRequest, AuthRegisterRequest, AuthSessionResponse, AuthUser
from app.modules.auth.service import (
    get_current_user,
    get_current_user_token,
    login_user,
    logout_user,
    register_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionResponse, summary="Register a new account")
async def register_route(
    request: AuthRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    return await register_user(
        session=session,
        email=request.email,
        display_name=request.display_name,
        password=request.password,
    )


@router.post("/login", response_model=AuthSessionResponse, summary="Login with email and password")
async def login_route(
    request: AuthLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    return await login_user(session=session, email=request.email, password=request.password)


@router.get("/me", response_model=AuthUser, summary="Get current user")
async def me_route(current_user=Depends(get_current_user)) -> AuthUser:
    return AuthUser(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        created_at=current_user.created_at,
    )


@router.post("/logout", summary="Logout current session")
async def logout_route(
    token: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    await logout_user(session=session, token=token)
    return {"ok": True}
