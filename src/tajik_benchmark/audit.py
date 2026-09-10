from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict

from .models import BenchmarkItem
from .validation import complete_stimulus


def normalize_prompt(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def word_shingles(text: str, size: int = 5) -> set[str]:
    words = normalize_prompt(text).split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def audit_items(items: list[BenchmarkItem], near_duplicate_threshold: float = 0.82) -> dict:
    normalized = [normalize_prompt(complete_stimulus(item)) for item in items]
    exact_groups: dict[str, list[int]] = defaultdict(list)
    for index, text in enumerate(normalized):
        exact_groups[text].append(index)
    exact_duplicates = []
    for text, indexes in exact_groups.items():
        if text and len(indexes) > 1:
            exact_duplicates.append({
                "prompt_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "item_ids": [items[i].item_id for i in indexes],
                "splits": sorted({items[i].split for i in indexes}),
            })

    shingles = [word_shingles(text) for text in normalized]
    inverted: dict[str, list[int]] = defaultdict(list)
    for i, grams in enumerate(shingles):
        for gram in grams:
            inverted[gram].append(i)
    candidates: set[tuple[int, int]] = set()
    for indexes in inverted.values():
        if len(indexes) <= 100:
            for pos, left in enumerate(indexes):
                for right in indexes[pos + 1:]:
                    candidates.add((left, right))
    near_duplicates = []
    for left, right in sorted(candidates):
        union = shingles[left] | shingles[right]
        similarity = len(shingles[left] & shingles[right]) / len(union) if union else 0.0
        if similarity >= near_duplicate_threshold and normalized[left] != normalized[right]:
            near_duplicates.append({
                "left_id": items[left].item_id,
                "right_id": items[right].item_id,
                "left_split": items[left].split,
                "right_split": items[right].split,
                "jaccard_5gram": round(similarity, 4),
                "cross_split": items[left].split != items[right].split,
            })

    cells = Counter((x.split, x.category, x.register) for x in items)
    return {
        "item_count": len(items),
        "unique_item_ids": len({x.item_id for x in items}),
        "counts_by_split": dict(sorted(Counter(x.split for x in items).items())),
        "counts_by_category": dict(sorted(Counter(x.category for x in items).items())),
        "counts_by_register": dict(sorted(Counter(x.register for x in items).items())),
        "counts_by_split_category_register": [
            {"split": k[0], "category": k[1], "register": k[2], "n": v}
            for k, v in sorted(cells.items())
        ],
        "professor_validated": {
            "true": sum(x.professor_validated for x in items),
            "false": sum(not x.professor_validated for x in items),
            "rate": round(sum(x.professor_validated for x in items) / len(items), 4) if items else None,
        },
        "missing": {
            "prompt_tg": sum(not x.prompt_tg for x in items),
            "source": sum(not x.source for x in items),
            "subtype": sum(not x.subtype for x in items),
        },
        "exact_duplicate_groups": exact_duplicates,
        "near_duplicate_threshold": near_duplicate_threshold,
        "near_duplicate_pairs": near_duplicates,
        "cross_split_near_duplicate_pairs": sum(x["cross_split"] for x in near_duplicates),
    }


def stratified_review_sample(items: list[BenchmarkItem], per_cell: int = 3, seed: int = 20260819) -> list[dict]:
    groups: dict[tuple[str, str, str], list[BenchmarkItem]] = defaultdict(list)
    for item in items:
        groups[(item.split, item.category, item.register)].append(item)
    rng = random.Random(seed)
    rows = []
    for key in sorted(groups):
        candidates = groups[key][:]
        rng.shuffle(candidates)
        for item in candidates[:per_cell]:
            row = asdict(item)
            row.update({
                "review_status": "",
                "corrected_text": "",
                "corrected_prompt_tg": "",
                "corrected_option_a": "",
                "corrected_option_b": "",
                "corrected_gold_answer": "",
                "reviewer_name": "",
                "review_date": "",
                "review_comment": "",
            })
            rows.append(row)
    return rows
