"""Swappable classifier backend protocol.

To replace the bundled model with a different one, create a new class that
implements ClassifierBackend and pass it to PromptGuardClassifier(backend=...).

Example:
    class MyCustomBackend:
        def load(self) -> bool: ...
        def classify(self, text: str) -> dict[str, float]: ...
        def get_label(self) -> str: ...

    classifier = PromptGuardClassifier(backend=MyCustomBackend())
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ClassifierBackend(Protocol):
    """Protocol that any classifier model backend must implement.

    Implementing this protocol is the ONLY thing needed to swap in a
    different detection model — no other code changes required.
    """

    def load(self) -> bool:
        """Load model weights into memory. Return True on success."""
        ...

    def classify(self, text: str) -> dict[str, float]:
        """Run inference on text. Return dict with keys:
        - 'benign':    probability the text is safe (0.0 – 1.0)
        - 'injection': probability of prompt injection (0.0 – 1.0)
        - 'jailbreak': probability of jailbreak attempt (0.0 – 1.0)
        """
        ...

    def get_label(self) -> str:
        """Short human-readable label shown in the UI status bar."""
        ...

    @property
    def is_loaded(self) -> bool:
        """True if model weights are in memory and ready for inference."""
        ...
