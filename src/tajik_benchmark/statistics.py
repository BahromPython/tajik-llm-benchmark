from __future__ import annotations

import math
from collections import defaultdict


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return (math.nan, math.nan)
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return center - margin, center + margin


def summarize_accuracy(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row.get("objective_correct") not in ("", None):
            key = (row["model"], row["condition"], row["category"])
            groups[key].append(float(row["objective_correct"]))
    result = []
    for (model, condition, category), values in sorted(groups.items()):
        successes = int(sum(values)); total = len(values)
        low, high = wilson_interval(successes, total)
        result.append(
            {
                "model": model,
                "condition": condition,
                "category": category,
                "correct": successes,
                "n": total,
                "accuracy": successes / total,
                "ci95_low": low,
                "ci95_high": high,
            }
        )
    return result


def summarize_efficiency(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["condition"])].append(row)
    result = []
    for (model, condition), values in sorted(groups.items()):
        def numbers(field):
            return [float(v[field]) for v in values if v.get(field) not in ("", None)]
        totals = numbers("total_tokens")
        latencies = sorted(numbers("latency_ms"))
        costs = numbers("estimated_cost_usd")
        correct = [float(v["objective_correct"]) for v in values if v.get("objective_correct") not in ("", None)]
        correct_n = int(sum(correct))
        result.append({
            "model": model,
            "condition": condition,
            "n": len(values),
            "total_tokens": sum(totals) if totals else None,
            "mean_tokens": sum(totals) / len(totals) if totals else None,
            "tokens_per_correct": sum(totals) / correct_n if totals and correct_n else None,
            "estimated_cost_usd": sum(costs) if costs else None,
            "cost_per_correct_usd": sum(costs) / correct_n if costs and correct_n else None,
            "median_latency_ms": latencies[len(latencies)//2] if latencies else None,
            "retry_count": sum(int(float(v.get("retry_count") or 0)) for v in values),
            "failure_count": sum((v.get("request_status") or "ok") != "ok" for v in values),
            "format_violation_rate": sum(str(v.get("format_violation", "")).lower() in {"1", "true"} for v in values) / len(values),
        })
    return result
