"""Generic HTTP provider — the primary provider for arbitrary AI application endpoints."""

import json
import time
from typing import Any
import httpx

from pit.config.models import APIConfig
from pit.providers.base import ConnectionTestResult, LLMProvider, LLMResponse


class GenericHTTPProvider(LLMProvider):
    """Calls any HTTP endpoint using the user-configured template, auth, and response path."""

    def __init__(self, config: APIConfig) -> None:
        self.config = config

    def _extract_json_path(self, data: Any, path: str) -> str:
        """Extract a string value from a nested dict/list using dot-notation."""
        if not path:
            return str(data) if data is not None else ""
        keys = path.split(".")
        current = data
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            elif isinstance(current, list) and k.isdigit():
                idx = int(k)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return ""
            if current is None:
                return ""
        return str(current) if current is not None else ""

    def _build_payload(self, prompt: str, system_prompt: str | None = None) -> Any:
        """Render the request template with prompt and system_prompt substituted."""
        tpl = self.config.request_template or '{"prompt": "{{prompt}}"}'
        sys_prompt = system_prompt if system_prompt is not None else (self.config.system_prompt or "")

        # Safe JSON-string escaping (strip surrounding quotes added by json.dumps)
        escaped_prompt = json.dumps(prompt)[1:-1]
        escaped_sys = json.dumps(sys_prompt)[1:-1]

        rendered = (
            tpl
            .replace("{{prompt}}", escaped_prompt)
            .replace("{{system_prompt}}", escaped_sys)
        )
        try:
            return json.loads(rendered)
        except Exception:
            return rendered

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers, injecting the API key via the configured auth scheme."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.api_key.strip():
            header_val = self.config.build_auth_header_value()
            if header_val.strip():
                headers[self.config.auth_header_name.strip() or "Authorization"] = header_val
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
        return headers

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        url = self.config.effective_endpoint
        if not url:
            return LLMResponse(
                content="",
                status_code=0,
                error="Endpoint URL is not configured. Set it in the 'Target AI Application' section.",
            )

        headers = self._build_headers()
        payload = self._build_payload(prompt, system_prompt)
        method = (self.config.http_method or "POST").upper()
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                if isinstance(payload, dict):
                    response = await client.request(method, url, json=payload, headers=headers)
                else:
                    response = await client.request(method, url, content=str(payload), headers=headers)

                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code >= 400:
                    return LLMResponse(
                        content="",
                        raw_response={"status_code": response.status_code, "body": response.text[:500]},
                        latency_ms=latency_ms,
                        status_code=response.status_code,
                        error=f"HTTP {response.status_code}: {response.text[:300]}",
                    )

                try:
                    data = response.json()
                    content = self._extract_json_path(data, self.config.response_path)
                except Exception:
                    data = {"raw": response.text[:500]}
                    content = response.text

                return LLMResponse(
                    content=content,
                    raw_response=data if isinstance(data, dict) else {"data": data},
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
            resp = await self.generate(prompt="ping", system_prompt="Answer pong")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            endpoint_label = self.config.effective_endpoint or "Unconfigured"
            if resp.is_success:
                return ConnectionTestResult(
                    success=True,
                    model=self.config.model or endpoint_label,
                    latency_ms=round(resp.latency_ms or latency_ms, 1),
                    message="Connection successful",
                    details={"sample_reply": resp.content.strip()[:80]},
                )
            return ConnectionTestResult(
                success=False,
                model=self.config.model or endpoint_label,
                latency_ms=round(latency_ms, 1),
                message=resp.error or "Connection failed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ConnectionTestResult(
                success=False,
                model=self.config.model or "Endpoint",
                latency_ms=round(latency_ms, 1),
                message=str(e),
            )
