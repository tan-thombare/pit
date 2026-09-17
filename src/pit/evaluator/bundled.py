"""Local HuggingFace transformer backend for the prompt-injection classifier.

The model is stored in:
    src/pit/evaluator/bundled_model/     ← shipped with the source tree (preferred)

If the bundled_model directory is absent (e.g. a fresh clone), the model is
downloaded from Hugging Face on first run and cached in the standard HF cache
directory (~/.cache/huggingface/hub/). Subsequent runs load from that cache
instantly without any network access.

The user never sees any of this — the startup splash screen handles the first-run
download transparently.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Default model ─────────────────────────────────────────────────────────────
DEFAULT_MODEL_NAME: str = "protectai/deberta-v3-base-prompt-injection-v2"


def _bundled_model_dir(model_name: str) -> Path | None:
    """Return the local directory containing pre-bundled model weights, or None.

    Resolution order:
    1. <evaluator pkg dir>/bundled_model/  — shipped alongside the source code
    2. Returns None → caller falls back to HF cache
    """
    pkg_dir = Path(__file__).parent
    candidate = pkg_dir / "bundled_model"
    if candidate.exists() and any(candidate.iterdir()):
        return candidate
    return None


class BundledModelBackend:
    """Transformer-based classifier backend that prefers the bundled model directory.

    This is the default backend used in the packaged .exe. It requires no network
    access — all model weights are shipped with the application.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device
        self._tokenizer: Any = None
        self._model: Any = None
        self._loaded = False

    # ── ClassifierBackend protocol ────────────────────────────────────────────

    def get_label(self) -> str:
        slug = self._model_name.split("/")[-1]
        src = "bundled" if _bundled_model_dir(self._model_name) else "HF cache"
        return f"{slug} ({src})"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> bool:
        """Load tokenizer and model into memory from the bundled path or HF cache."""
        if self._loaded:
            return True

        model_dir = _bundled_model_dir(self._model_name)
        load_path: str | Path = model_dir if model_dir else self._model_name
        local_only = model_dir is not None  # never go to network when bundled

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info("Loading classifier from %s on %s ...", load_path, self._device)
            self._tokenizer = AutoTokenizer.from_pretrained(
                str(load_path), local_files_only=local_only
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                str(load_path), local_files_only=local_only
            )
            self._model.to(self._device)
            self._model.eval()
            self._loaded = True
            logger.info("Classifier loaded successfully.")
            return True
        except Exception as exc:
            logger.warning("Failed to load classifier from %s: %s", load_path, exc)
            self._loaded = False
            return False

    def classify(self, text: str) -> dict[str, float]:
        """Run inference; returns probabilities for benign / injection / jailbreak."""
        if not (self._loaded and self._model and self._tokenizer):
            return _heuristic_fallback(text)

        try:
            import torch

            inputs = self._tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512
            ).to(self._device)

            with torch.no_grad():
                logits = self._model(**inputs).logits
                probs_tensor = torch.softmax(logits, dim=-1).squeeze()
                probs = probs_tensor.tolist()

            return _probs_to_dict(self._model, probs)
        except Exception as exc:
            logger.error("Inference error: %s", exc)
            return _heuristic_fallback(text)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _probs_to_dict(model: Any, probs: list[float] | float) -> dict[str, float]:
    """Map raw probability tensor to the canonical {benign, injection, jailbreak} dict."""
    if isinstance(probs, float):
        return {"benign": 1.0 - probs, "injection": probs, "jailbreak": 0.0}

    prob_list = list(probs)

    # Use id2label if available
    if hasattr(model, "config") and hasattr(model.config, "id2label") and model.config.id2label:
        id2label = model.config.id2label
        res = {"benign": 0.0, "injection": 0.0, "jailbreak": 0.0}
        if len(prob_list) == 1:
            prob_list = [1.0 - prob_list[0], prob_list[0]]
        for idx, p in enumerate(prob_list):
            lbl = str(id2label.get(idx, id2label.get(str(idx), ""))).upper()
            if "SAFE" in lbl or "BENIGN" in lbl:
                res["benign"] = float(p)
            elif "INJ" in lbl:
                res["injection"] = float(p)
            elif "JAIL" in lbl:
                res["jailbreak"] = float(p)
        return res

    if len(prob_list) == 2:
        return {"benign": float(prob_list[0]), "injection": float(prob_list[1]), "jailbreak": 0.0}
    if len(prob_list) >= 3:
        return {
            "benign": float(prob_list[0]),
            "injection": float(prob_list[1]),
            "jailbreak": float(prob_list[2]),
        }
    return {"benign": 1.0, "injection": 0.0, "jailbreak": 0.0}


def _heuristic_fallback(text: str) -> dict[str, float]:
    """Lightweight keyword heuristic used when model is not loaded."""
    lower = text.lower()
    keywords = [
        "ignore all previous", "override", "bypass", "system prompt",
        "jailbreak", "unrestricted", "dan mode", "developer mode",
    ]
    score = min(sum(0.25 for kw in keywords if kw in lower), 0.95)
    return {"benign": 1.0 - score, "injection": score, "jailbreak": score * 0.5}
