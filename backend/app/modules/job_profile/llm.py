from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

import httpx
from zai import ZhipuAiClient

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class JobProfileLLMClient(Protocol):
    provider_name: str

    async def extract(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        ...


class HeuristicJobProfileLLMClient:
    provider_name = "heuristic"

    async def extract(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        return None


class OpenAICompatibleJobProfileLLMClient:
    provider_name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def extract(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        endpoint = self.base_url
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Job profile LLM request failed: %s", exc)
            return None

        try:
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if not isinstance(content, str):
                return None
            return json.loads(content)
        except Exception as exc:
            logger.warning("Job profile LLM response parse failed: %s", exc)
            return None


class ZaiSDKJobProfileLLMClient:
    provider_name = "zai_sdk"

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def extract(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        def _request() -> Any:
            client = ZhipuAiClient(api_key=self.api_key)
            return client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
                temperature=0.1,
            )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(_request),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            logger.warning("Job profile ZAI SDK request failed: %s", exc)
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
            if not isinstance(content, str):
                content = str(content or "")
            return json.loads(content)
        except Exception as exc:
            logger.warning("Job profile ZAI SDK response parse failed: %s", exc)
            return None


def build_job_profile_llm_client() -> JobProfileLLMClient:
    provider = settings.job_profile_llm_provider.lower().strip()
    if provider in {"zai_sdk", "zai", "zhipu"} and settings.job_profile_llm_api_key:
        return ZaiSDKJobProfileLLMClient(
            api_key=settings.job_profile_llm_api_key,
            model=settings.job_profile_llm_model,
            timeout_seconds=settings.job_profile_llm_timeout_seconds,
        )
    if (
        provider == "openai_compatible"
        and settings.job_profile_llm_base_url
        and settings.job_profile_llm_api_key
    ):
        return OpenAICompatibleJobProfileLLMClient(
            base_url=settings.job_profile_llm_base_url,
            api_key=settings.job_profile_llm_api_key,
            model=settings.job_profile_llm_model,
            timeout_seconds=settings.job_profile_llm_timeout_seconds,
        )
    return HeuristicJobProfileLLMClient()

# AI辅助生成：Qwen3-Max-Thinking, 2026-04-27