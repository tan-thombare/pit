"""Anthropic Messages API provider."""

import time
from typing import Any
import httpx

from pit.config.models import APIConfig
from pit.providers.base import ConnectionTestResult, LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic's Messages API."""

    def __init__(self, config: APIConfig) -> None:
        self.config = config
        self.base_url = self._format_base_url(config.base_url)

    def _format_base_url(self, raw_url: str) -> str:
        url = (raw_url or "https://api.anthropic.com/v1").rstrip("/")
        if not url.endswith("/messages"):
            url = f"{url}/messages"
        return url

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.config.api_key.strip():
            headers["x-api-key"] = self.config.api_key.strip()
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
        return headers

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        sys_prompt = system_prompt if system_prompt is not None else self.config.system_prompt
        if sys_prompt and sys_prompt.strip():
            payload["system"] = sys_prompt

        headers = self._build_headers()
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text[:300]}"
                    try:
                        err_json = response.json()
                        if "error" in err_json and isinstance(err_json["error"], dict):
                            error_msg = f"Anthropic Error ({response.status_code}): {err_json['error'].get('message', '')}"
                    except Exception:
                        pass
                    return LLMResponse(
                        content="",
                        raw_response={"status_code": response.status_code, "body": response.text[:500]},
                        latency_ms=latency_ms,
                        status_code=response.status_code,
                        error=error_msg,
                    )

                data = response.json()
                content = ""
                content_blocks = data.get("content", [])
                if isinstance(content_blocks, list):
                    text_parts = [
                        b.get("text", "") for b in content_blocks if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    content = "".join(text_parts)

                return LLMResponse(
                    content=content,
                    raw_response=data,
                    latency_ms=latency_ms,
                    status_code=response.status_code,
                    error=None,
                )

        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return LLMResponse(
                content="",
                latency_ms=latency_ms,
                status_code=408,
                error=f"Request timed out after {self.config.timeout_seconds}s",
            )
        except httpx.RequestError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return LLMResponse(
                content="",
                latency_ms=latency_ms,
                status_code=0,
                error=f"Network error: {str(e)}",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return LLMResponse(
                content="",
                latency_ms=latency_ms,
                status_code=500,
                error=f"Unexpected error: {str(e)}",
            )

    async def test_connection(self) -> ConnectionTestResult:
        start_time = time.perf_counter()
        try:
            resp = await self.generate(prompt="ping", system_prompt="Answer in 1 word: pong")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            if resp.is_success:
                return ConnectionTestResult(
                    success=True,
                    model=self.config.model,
                    latency_ms=round(resp.latency_ms or latency_ms, 1),
                    message="Connection successful",
                    details={"sample_reply": resp.content.strip()[:60]},
                )
            return ConnectionTestResult(
                success=False,
                model=self.config.model,
                latency_ms=round(latency_ms, 1),
                message=resp.error or "Connection failed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ConnectionTestResult(
                success=False,
                model=self.config.model,
                latency_ms=round(latency_ms, 1),
                message=str(e),
            )
