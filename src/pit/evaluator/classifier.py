"""Local classifier facade — thin wrapper around a swappable ClassifierBackend.

The default backend is BundledModelBackend which ships with the application.
To use a different model, pass a custom backend that implements ClassifierBackend.
"""

import logging
import threading
from typing import Callable

from pydantic import BaseModel

from pit.evaluator.backend import ClassifierBackend
from pit.evaluator.bundled import BundledModelBackend, DEFAULT_MODEL_NAME

logger = logging.getLogger(__name__)

# Re-export so existing import sites don't break:  from pit.evaluator.classifier import DEFAULT_MODEL_NAME
__all__ = ["PromptGuardClassifier", "ClassifierStatus", "DEFAULT_MODEL_NAME"]


class ClassifierStatus(BaseModel):
    """Health and load status of the active classifier backend."""
    model_name: str
    is_installed: bool   # weights present on disk
    is_loaded: bool      # weights in memory and ready for inference
    device: str
    error: str | None = None


class PromptGuardClassifier:
    """Facade that exposes classifier functionality to the rest of the application.

    All actual model logic lives in the backend. Swapping backends is the only
    change needed to use a different model.

    Usage (default bundled model):
        clf = PromptGuardClassifier()

    Usage (custom backend):
        clf = PromptGuardClassifier(backend=MyONNXBackend())
    """

    def __init__(
        self,
        backend: ClassifierBackend | None = None,
        # Legacy kwargs kept for backwards compatibility with app.py / config:
        model_name: str = DEFAULT_MODEL_NAME,
        preferred_device: str = "auto",
    ) -> None:
        resolved_device = self._resolve_device(preferred_device)
        self._backend: ClassifierBackend = backend or BundledModelBackend(
            model_name=model_name,
            device=resolved_device,
        )
        self._device = resolved_device
        self._load_lock = threading.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def model_name(self) -> str:
        """Human-readable label for the active backend (shown in status UI)."""
        return self._backend.get_label()

    @property
    def device(self) -> str:
        return self._device

    @property
    def _is_loaded(self) -> bool:
        return self._backend.is_loaded

    def get_status(self) -> ClassifierStatus:
        """Return current classifier status for the Config tab status card."""
        loaded = self._backend.is_loaded
        from pit.evaluator.bundled import _bundled_model_dir
        is_installed = _bundled_model_dir(DEFAULT_MODEL_NAME) is not None or self._hf_cache_present()

        return ClassifierStatus(
            model_name=self._backend.get_label(),
            is_installed=is_installed,
            is_loaded=loaded,
            device=self._device.upper(),
        )

    def load_model(self, force_reload: bool = False) -> bool:
        """Load the backend model into memory (thread-safe)."""
        if self._backend.is_loaded and not force_reload:
            return True
        with self._load_lock:
            return self._backend.load()

    def download_model(self, status_callback: Callable[[str], None] | None = None) -> bool:
        """Download / reload model weights (used when NOT bundled, i.e. dev mode).

        When running the packaged .exe the model is already bundled, so this
        simply calls load() on the backend.
        """
        from pit.evaluator.bundled import _bundled_model_dir
        if _bundled_model_dir(DEFAULT_MODEL_NAME):
            # Bundled path exists — just load, no network needed
            if status_callback:
                status_callback("Loading bundled model into memory...")
            ok = self._backend.load()
            if status_callback:
                msg = "Bundled model loaded." if ok else "Failed to load bundled model."
                status_callback(msg)
            return ok

        # Dev mode: fall back to HF download
        if status_callback:
            status_callback(f"Downloading {DEFAULT_MODEL_NAME} from Hugging Face...")
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            AutoTokenizer.from_pretrained(DEFAULT_MODEL_NAME)
            AutoModelForSequenceClassification.from_pretrained(DEFAULT_MODEL_NAME)
            if status_callback:
                status_callback("Download complete. Loading into memory...")
            ok = self._backend.load()
            if status_callback:
                status_callback("Model ready." if ok else "Load failed after download.")
            return ok
        except Exception as exc:
            logger.error("Download failed: %s", exc)
            if status_callback:
                status_callback(f"Download error: {exc}")
            return False

    def classify(self, text: str) -> dict[str, float]:
        """Run inference on text. Returns {benign, injection, jailbreak} probabilities."""
        if not text.strip():
            return {"benign": 1.0, "injection": 0.0, "jailbreak": 0.0}
        return self._backend.classify(text)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_device(preferred: str) -> str:
        if preferred.lower() == "cpu":
            return "cpu"
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _hf_cache_present(self) -> bool:
        """Check if model is cached in the Hugging Face local cache."""
        try:
            from huggingface_hub import try_to_load_from_cache
            import os
            cached = try_to_load_from_cache(DEFAULT_MODEL_NAME, "config.json")
            return isinstance(cached, str) and os.path.exists(cached)
        except Exception:
            return False
