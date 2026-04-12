from fastapi import APIRouter, Depends

from app.modules.assistant.schema import AssistantChatRequest, AssistantChatResponse
from app.modules.assistant.service import generate_assistant_reply
from app.modules.auth.service import get_current_user

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse, summary="Chat with the AI assistant")
async def assistant_chat_route(
    request: AssistantChatRequest,
    _current_user=Depends(get_current_user),
) -> AssistantChatResponse:
    reply, provider, model = await generate_assistant_reply(request)
    return AssistantChatResponse(
        reply=reply,
        provider=provider,
        model=model,
        used_context=request.context is not None,
    )
