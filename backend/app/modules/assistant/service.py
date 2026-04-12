from __future__ import annotations

import asyncio
from typing import Any, Protocol

import httpx
from zai import ZhipuAiClient

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.modules.assistant.schema import AssistantChatRequest

settings = get_settings()
logger = get_logger(__name__)


class AssistantLLMClient(Protocol):
    provider_name: str
    model_name: str

    async def chat(self, messages: list[dict[str, str]]) -> str | None:
        ...


class OpenAICompatibleAssistantLLMClient:
    provider_name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds

    async def chat(self, messages: list[dict[str, str]]) -> str | None:
        endpoint = self.base_url
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"

        payload = {
            "model": self.model_name,
            "temperature": 0.5,
            "messages": messages,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Assistant OpenAI-compatible request failed: %s", exc)
            return None

        try:
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text", "")))
                content = "".join(parts)
            return str(content).strip()
        except Exception as exc:
            logger.warning("Assistant OpenAI-compatible response parse failed: %s", exc)
            return None


class ZaiSDKAssistantLLMClient:
    provider_name = "zai_sdk"

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds

    async def chat(self, messages: list[dict[str, str]]) -> str | None:
        def _request() -> Any:
            client = ZhipuAiClient(api_key=self.api_key)
            return client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                thinking={"type": "enabled"},
                max_tokens=4096,
                temperature=0.5,
            )

        try:
            response = await asyncio.wait_for(asyncio.to_thread(_request), timeout=self.timeout_seconds)
        except Exception as exc:
            logger.warning("Assistant ZAI SDK request failed: %s", exc)
            return None

        try:
            message = response.choices[0].message
            content = getattr(message, "content", None)
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(str(getattr(item, "text", "")))
                content = "".join(parts)
            return str(content or "").strip()
        except Exception as exc:
            logger.warning("Assistant ZAI SDK response parse failed: %s", exc)
            return None


def _resolve_provider() -> str:
    return (
        settings.assistant_llm_provider
        or settings.reporting_llm_provider
        or settings.job_profile_llm_provider
        or "heuristic"
    ).strip().lower()


def _resolve_base_url() -> str | None:
    return settings.assistant_llm_base_url or settings.reporting_llm_base_url or settings.job_profile_llm_base_url


def _resolve_api_key() -> str | None:
    return settings.assistant_llm_api_key or settings.reporting_llm_api_key or settings.job_profile_llm_api_key


def _resolve_model() -> str:
    return (
        settings.assistant_llm_model
        or settings.reporting_llm_model
        or settings.job_profile_llm_model
        or "career-assistant"
    )


def _resolve_timeout() -> int:
    return (
        settings.assistant_llm_timeout_seconds
        or settings.reporting_llm_timeout_seconds
        or settings.job_profile_llm_timeout_seconds
        or 30
    )


def build_assistant_llm_client() -> AssistantLLMClient:
    provider = _resolve_provider()
    base_url = _resolve_base_url()
    api_key = _resolve_api_key()
    model = _resolve_model()
    timeout_seconds = _resolve_timeout()

    if provider in {"zai_sdk", "zai", "zhipu"} and api_key:
        return ZaiSDKAssistantLLMClient(api_key=api_key, model=model, timeout_seconds=timeout_seconds)
    if provider == "openai_compatible" and base_url and api_key:
        return OpenAICompatibleAssistantLLMClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    raise AppException(
        message="AI assistant is not configured. Please check assistant/job-profile/reporting LLM settings.",
        error_code="assistant_not_configured",
        status_code=503,
    )


def _build_system_prompt() -> str:
    return (
        "You are an AI career planning assistant embedded inside a career planning web app. "
        "Help users understand the system, career planning workflow, job recommendations, resumes, and reports. "
        "Be concise, practical, and supportive. "
        "If the user asks you to perform an action in the product, explain the best next step clearly because this phase is chat-first. "
        "Do not invent records, IDs, or analysis results that were not provided in context. "
        "If page context is provided, use it to tailor the answer."
    )


def _build_context_block(request: AssistantChatRequest) -> str | None:
    if request.context is None:
        return None

    lines = [
        f"Current page: {request.context.page_name}",
    ]
    if request.context.page_label:
        lines.append(f"Page label: {request.context.page_label}")
    if request.context.student_profile_id is not None:
        lines.append(f"Student profile ID: {request.context.student_profile_id}")
    if request.context.report_id is not None:
        lines.append(f"Report ID: {request.context.report_id}")
    if request.context.resume_id is not None:
        lines.append(f"Resume ID: {request.context.resume_id}")
    if request.context.notes:
        lines.append(f"Context notes: {request.context.notes}")
    return "\n".join(lines)


def _build_messages(request: AssistantChatRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": _build_system_prompt()}]
    context_block = _build_context_block(request)
    if context_block:
        messages.append({"role": "system", "content": context_block})
    messages.extend({"role": message.role, "content": message.content} for message in request.messages[-12:])
    return messages


async def generate_assistant_reply(request: AssistantChatRequest) -> tuple[str, str, str]:
    client = build_assistant_llm_client()
    reply = await client.chat(_build_messages(request))
    if not reply:
        raise AppException(
            message="AI assistant is temporarily unavailable. Please try again later.",
            error_code="assistant_generation_failed",
            status_code=502,
        )
    return reply, client.provider_name, client.model_name
