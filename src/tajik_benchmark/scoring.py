from __future__ import annotations

import re


def normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())


def score_objective(item: dict, response: str) -> tuple[str, float | None]:
    if item["category"] == "grammar":
        match = re.search(r"\b([AB])\b", response.upper())
        prediction = match.group(1) if match else ""
        return prediction, float(prediction == item["gold_answer"].upper())
    if item["category"] == "factual" and (item.get("gold_answer") or item.get("reference_answer")):
        gold = normalize(item.get("gold_answer") or item.get("reference_answer", ""))
        prediction = normalize(response)
        return prediction, float(gold in prediction or prediction in gold)
    return "", None


def response_quality_flags(item: dict, response: str) -> dict:
    expected = (item.get("response_format") or "").casefold()
    stripped = response.strip()
    words = stripped.split()
    format_violation = False
    if item["category"] == "grammar":
        format_violation = not bool(re.fullmatch(r"\s*[AB]\s*", stripped, flags=re.IGNORECASE))
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*words?", expected)
    if match:
        low, high = map(int, match.groups())
        format_violation = format_violation or not (low <= len(words) <= high)
    return {
        "response_words": len(words),
        "response_characters": len(stripped),
        "format_violation": format_violation,
        "empty_response": not bool(stripped),
    }
