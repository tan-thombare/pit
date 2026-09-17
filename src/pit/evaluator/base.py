"""Base protocols and abstract interfaces for response evaluators."""

from typing import Protocol, runtime_checkable

from pit.attacks.models import Attack
from pit.evaluator.models import EvaluationContext, EvaluationResult


@runtime_checkable
class ResponseEvaluator(Protocol):
    """Protocol defining the interface for response evaluators."""

    def evaluate(
        self,
        attack: Attack,
        response: str,
        context: EvaluationContext | None = None,
    ) -> EvaluationResult:
        """Evaluate whether a target response succumbed to or resisted an attack."""
        ...
