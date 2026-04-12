from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schema import AuthLoginRequest, AuthProfileUpdateRequest, AuthRegisterRequest, AuthSessionResponse, AuthUser
from app.modules.auth.service import (
    delete_user_account,
    get_current_user,
    get_current_user_token,
    login_user,
    logout_user,
    register_user,
    update_user_profile,
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


@router.patch("/me", response_model=AuthUser, summary="Update current user profile")
async def update_me_route(
    request: AuthProfileUpdateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUser:
    return await update_user_profile(
        session=session,
        user=current_user,
        email=request.email,
        display_name=request.display_name,
        current_password=request.current_password,
        new_password=request.new_password,
    )


@router.delete("/me", summary="Delete current user account")
async def delete_me_route(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    await delete_user_account(session=session, user=current_user)
    return {"ok": True}


@router.post("/logout", summary="Logout current session")
async def logout_route(
    token: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    await logout_user(session=session, token=token)
    return {"ok": True}
