"""Base abstractions for LLM API providers."""

from abc import ABC, abstractmethod
import time
from typing import Any
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Normalized response from an LLM provider."""
    content: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    status_code: int = 200
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None and bool(self.content.strip() or self.status_code == 200)


class ConnectionTestResult(BaseModel):
    """Result of a connection test."""
    success: bool
    model: str
    latency_ms: float
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for all LLM API providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send a prompt to the target LLM API and return the response."""
        ...

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Perform a harmless minimal request to verify connectivity and credentials."""
        ...
