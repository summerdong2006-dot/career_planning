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


class ReportingLLMClient(Protocol):
    provider_name: str

    async def extract(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        ...


class HeuristicReportingLLMClient:
    provider_name = "heuristic"

    async def extract(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        return None


class OpenAICompatibleReportingLLMClient:
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
            "temperature": 0.3,
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
            logger.warning("Reporting LLM request failed: %s", exc)
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
            logger.warning("Reporting LLM response parse failed: %s", exc)
            return None


class ZaiSDKReportingLLMClient:
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
                thinking={"type": "enabled"},
                max_tokens=8192,
                temperature=0.3,
            )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(_request),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            logger.warning("Reporting ZAI SDK request failed: %s", exc)
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
            logger.warning("Reporting ZAI SDK response parse failed: %s", exc)
            return None


def build_reporting_llm_client() -> ReportingLLMClient:
    provider = (settings.reporting_llm_provider or settings.job_profile_llm_provider).lower().strip()
    base_url = settings.reporting_llm_base_url or settings.job_profile_llm_base_url
    api_key = settings.reporting_llm_api_key or settings.job_profile_llm_api_key
    model = settings.reporting_llm_model or settings.job_profile_llm_model or "job-profile-extractor"
    timeout_seconds = settings.reporting_llm_timeout_seconds or settings.job_profile_llm_timeout_seconds

    if provider in {"zai_sdk", "zai", "zhipu"} and api_key:
        return ZaiSDKReportingLLMClient(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    if provider == "openai_compatible" and base_url and api_key:
        return OpenAICompatibleReportingLLMClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    return HeuristicReportingLLMClient()
# AI辅助生成：Qwen3-Max-Thinking, 2026-04-27