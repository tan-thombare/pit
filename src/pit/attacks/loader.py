"""Attack suite loader and filtering utilities."""

import json
import logging
from pathlib import Path

from pit.attacks.models import Attack, AttackCategory, AttackSeverity

logger = logging.getLogger(__name__)

BUILTIN_ATTACKS_PATH = Path(__file__).parent / "builtin" / "attacks.json"


def load_attacks(custom_path: Path | str | None = None) -> list[Attack]:
    """Load attacks from a JSON file (defaults to the built-in attack library)."""
    target_path = Path(custom_path) if custom_path else BUILTIN_ATTACKS_PATH
    if not target_path.exists():
        logger.error("Attacks file not found at %s", target_path)
        return []

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.error("Attacks file must contain a JSON array of attacks.")
            return []

        attacks = [Attack.model_validate(item) for item in data]
        return attacks
    except Exception as e:
        logger.error("Failed to parse attacks from %s: %s", target_path, e)
        return []


def filter_attacks(
    attacks: list[Attack],
    categories: list[AttackCategory | str] | None = None,
    severities: list[AttackSeverity | str] | None = None,
    query: str | None = None,
) -> list[Attack]:
    """Filter attack list by categories, severities, or a search query."""
    filtered = attacks

    if categories:
        cat_values = {c.value if isinstance(c, AttackCategory) else str(c) for c in categories}
        filtered = [a for a in filtered if a.category.value in cat_values]

    if severities:
        sev_values = {s.value if isinstance(s, AttackSeverity) else str(s) for s in severities}
        filtered = [a for a in filtered if a.severity.value in sev_values]

    if query and query.strip():
        q = query.strip().lower()
        filtered = [
            a for a in filtered
            if q in a.id.lower() or q in a.name.lower() or q in a.description.lower() or q in a.prompt.lower()
        ]

    return filtered
