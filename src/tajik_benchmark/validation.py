from __future__ import annotations

from collections import Counter
import unicodedata

from .models import ALLOWED_CATEGORIES, ALLOWED_REGISTERS, ALLOWED_SPLITS, BenchmarkItem


def complete_stimulus(item: BenchmarkItem) -> str:
    if item.category == "grammar":
        return f"{item.prompt_tg}\nA:{item.option_a}\nB:{item.option_b}"
    return item.prompt_tg


def validate_items(items: list[BenchmarkItem]) -> list[str]:
    errors: list[str] = []
    counts = Counter(item.item_id for item in items)
    for item_id, count in counts.items():
        if not item_id:
            errors.append("An item has an empty item_id")
        elif count > 1:
            errors.append(f"Duplicate item_id: {item_id}")
    for item in items:
        prefix = item.item_id or "<missing-id>"
        if item.split not in ALLOWED_SPLITS:
            errors.append(f"{prefix}: invalid split {item.split!r}")
        if item.category not in ALLOWED_CATEGORIES:
            errors.append(f"{prefix}: invalid category {item.category!r}")
        if item.register not in ALLOWED_REGISTERS:
            errors.append(f"{prefix}: invalid register {item.register!r}")
        if not item.prompt_tg:
            errors.append(f"{prefix}: prompt_tg is required")
        elif unicodedata.normalize("NFC", item.prompt_tg) != item.prompt_tg:
            errors.append(f"{prefix}: prompt_tg is not Unicode NFC normalized")
        if item.category == "grammar":
            if not item.option_a or not item.option_b:
                errors.append(f"{prefix}: grammar items require option_a and option_b")
            if item.gold_answer.upper() not in {"A", "B"}:
                errors.append(f"{prefix}: grammar gold_answer must be A or B")
            if item.option_a.strip().casefold() == item.option_b.strip().casefold():
                errors.append(f"{prefix}: grammar options must be different")
        if item.category == "factual" and not (item.gold_answer or item.reference_answer):
            errors.append(f"{prefix}: factual items require a gold or reference answer")
    return errors


def assert_no_overlap(items: list[BenchmarkItem]) -> None:
    normalized: dict[str, set[str]] = {}
    for item in items:
        key = " ".join(complete_stimulus(item).casefold().split())
        normalized.setdefault(key, set()).add(item.split)
    overlaps = {text: splits for text, splits in normalized.items() if len(splits) > 1}
    if overlaps:
        examples = list(overlaps.items())[:5]
        raise ValueError(f"Identical prompts occur across splits: {examples}")
