"""Configuration models for Prompt Injection Tester."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported LLM provider types (used as presets)."""
    OPENAI_COMPATIBLE = "openai_compatible"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GENERIC_HTTP = "generic_http"


class AuthPreset(str, Enum):
    """Common authentication header presets."""
    BEARER_TOKEN = "Bearer Token"         # Authorization: Bearer <key>
    API_KEY_HEADER = "API Key Header"     # x-api-key: <key>
    CUSTOM = "Custom"                     # fully custom header + value template


# Auth preset → (header name, value template using {{api_key}})
AUTH_PRESET_DEFAULTS: dict[str, tuple[str, str]] = {
    AuthPreset.BEARER_TOKEN: ("Authorization", "Bearer {{api_key}}"),
    AuthPreset.API_KEY_HEADER: ("x-api-key", "{{api_key}}"),
    AuthPreset.CUSTOM: ("Authorization", "Bearer {{api_key}}"),
}


class APIConfig(BaseModel):
    """Configuration for the target AI application endpoint."""

    # ── Primary endpoint settings ────────────────────────────────────────
    endpoint_url: str = Field(
        default="",
        description="Target endpoint URL (e.g. https://your-chatbot.com/api/chat)",
    )
    api_key: str = Field(default="", description="API key / token (masked in UI)")

    # ── Authentication customisation ─────────────────────────────────────
    auth_preset: str = Field(
        default=AuthPreset.BEARER_TOKEN,
        description="Authentication preset determining how the API key is sent",
    )
    auth_header_name: str = Field(
        default="Authorization",
        description="HTTP header used to send the API key",
    )
    auth_value_template: str = Field(
        default="Bearer {{api_key}}",
        description="Header value template; use {{api_key}} as placeholder",
    )

    # ── Request / response mapping ────────────────────────────────────────
    request_template: str = Field(
        default='{"messages": [{"role": "user", "content": "{{prompt}}"}]}',
        description="JSON request body template; use {{prompt}} and {{system_prompt}}",
    )
    response_path: str = Field(
        default="choices.0.message.content",
        description="Dot-notation path to extract the reply text from the response JSON",
    )
    http_method: str = Field(default="POST", description="HTTP method")

    # ── Optional model/system hint (used by LLM provider presets) ────────
    model: str = Field(default="", description="Model name hint (sent in payload when using provider presets)")
    system_prompt: str | None = Field(
        default="You are a helpful, harmless, and honest assistant.",
        description="Optional system prompt injected into the request template",
    )

    # ── Advanced parameters ───────────────────────────────────────────────
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    custom_headers: dict[str, str] = Field(default_factory=dict)

    # ── Legacy / provider-preset fields (kept for back-compat) ───────────
    provider: ProviderType = Field(
        default=ProviderType.GENERIC_HTTP,
        description="Provider preset type (drives auto-fill of endpoint + template)",
    )
    base_url: str = Field(default="", description="Legacy base URL (used by LLM provider presets)")

    # Deprecated aliases kept so existing saved configs deserialise cleanly
    generic_url: str = Field(default="", exclude=True)
    generic_method: str = Field(default="POST", exclude=True)
    generic_request_template: str = Field(default="", exclude=True)
    generic_response_path: str = Field(default="", exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """Migrate legacy fields on first load."""
        if not self.endpoint_url:
            if self.generic_url:
                self.endpoint_url = self.generic_url
            elif self.base_url and self.provider == ProviderType.GENERIC_HTTP:
                self.endpoint_url = self.base_url
        if self.generic_request_template and self.request_template == APIConfig.model_fields["request_template"].default:
            self.request_template = self.generic_request_template
        if self.generic_response_path and self.response_path == APIConfig.model_fields["response_path"].default:
            self.response_path = self.generic_response_path

    def build_auth_header_value(self) -> str:
        """Render the auth header value with the real API key substituted."""
        return self.auth_value_template.replace("{{api_key}}", self.api_key.strip())

    @property
    def effective_endpoint(self) -> str:
        """Return the endpoint URL that should actually be called."""
        return self.endpoint_url.strip() or self.base_url.strip()

    def sanitized_dict(self) -> dict[str, Any]:
        """Return config with sensitive API key redacted."""
        data = self.model_dump()
        if data.get("api_key"):
            data["api_key"] = "********"
        return data


class EvaluatorConfig(BaseModel):
    """Configuration for the local response evaluator."""
    model_name: str = Field(
        default="protectai/deberta-v3-base-prompt-injection-v2",
        description="Local Hugging Face classifier model identifier"
    )
    device: str = Field(
        default="auto",
        description="Device to run on: auto, cpu, cuda"
    )
    injection_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    jailbreak_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class AppConfig(BaseModel):
    """Top-level application settings."""
    api: APIConfig = Field(default_factory=APIConfig)
    evaluator: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    concurrency: int = Field(default=1, ge=1, le=10, description="Concurrent attack workers")
    delay_seconds: float = Field(default=0.2, ge=0.0, le=10.0, description="Delay between requests")
    export_dir: str = Field(default="", description="Default export directory")
