"""Data models for local evaluation and scoring."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from pit.attacks.models import Attack


class Verdict(str, Enum):
    """Security evaluation outcome."""
    SAFE = "SAFE"
    SUSPECTED_BYPASS = "SUSPECTED BYPASS"
    SUCCESSFUL_INJECTION = "SUCCESSFUL INJECTION"
    ERROR = "ERROR"


class SignalType(str, Enum):
    """Origin category of an evaluation signal."""
    DETERMINISTIC = "deterministic"
    CLASSIFIER = "classifier"
    SEMANTIC = "semantic"


class EvaluationSignal(BaseModel):
    """Individual signal observed during evaluation."""
    name: str
    signal_type: SignalType
    weight: float = Field(default=1.0, description="Importance weight of this signal")
    score: float = Field(
        default=0.0,
        description="Signal value: positive indicates bypass/injection, negative indicates safety/refusal"
    )
    triggered: bool = False
    description: str = ""


class EvaluationContext(BaseModel):
    """Contextual metadata passed to the evaluator."""
    system_prompt: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
    api_latency_ms: float = 0.0
    api_error: str | None = None
    target_model: str = ""


class EvaluationResult(BaseModel):
    """Final local evaluation result for an attack execution."""
    verdict: Verdict
    risk_score: float = Field(ge=0.0, le=100.0, description="Risk score from 0 (safest) to 100 (critical bypass)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the evaluation verdict")
    signals: list[EvaluationSignal] = Field(default_factory=list)
    reasoning: str = Field(description="Observable concise reasoning without exposing CoT")
    classifier_scores: dict[str, float] = Field(default_factory=dict)
    evaluator_device: str = "CPU"
    evaluation_latency_ms: float = 0.0
