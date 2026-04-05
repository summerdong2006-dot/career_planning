from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schema import WorkspaceOverviewResponse
from app.modules.auth.service import build_workspace_overview, get_current_user

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@router.get("/workspace", response_model=WorkspaceOverviewResponse, summary="Get current user workspace")
async def get_workspace_route(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceOverviewResponse:
    return await build_workspace_overview(session=session, user=current_user)
