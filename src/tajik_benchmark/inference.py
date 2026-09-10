from __future__ import annotations

import math
import random
from collections import defaultdict


def mcnemar_exact(b: int, c: int) -> dict:
    """Two-sided exact McNemar test from discordant counts."""
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "discordant": 0, "p_value": 1.0}
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2 ** n)
    return {"b": b, "c": c, "discordant": n, "p_value": min(1.0, 2 * tail)}


def paired_binary_comparison(rows: list[dict], baseline: str, treatment: str,
                             seed: int = 20260909, bootstrap_samples: int = 10_000) -> dict:
    by_key: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for row in rows:
        if row.get("objective_correct") in ("", None) or row.get("condition") not in {baseline, treatment}:
            continue
        by_key[(row["model"], row["item_id"])][row["condition"]] = int(float(row["objective_correct"]))
    pairs = [(v[baseline], v[treatment]) for v in by_key.values() if baseline in v and treatment in v]
    if not pairs:
        return {"baseline": baseline, "treatment": treatment, "n_pairs": 0}
    differences = [t - b for b, t in pairs]
    b_count = sum(b == 1 and t == 0 for b, t in pairs)
    c_count = sum(b == 0 and t == 1 for b, t in pairs)
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap_samples):
        boot.append(sum(differences[rng.randrange(len(differences))] for _ in differences) / len(differences))
    boot.sort()
    return {
        "baseline": baseline, "treatment": treatment, "n_pairs": len(pairs),
        "baseline_accuracy": sum(b for b, _ in pairs) / len(pairs),
        "treatment_accuracy": sum(t for _, t in pairs) / len(pairs),
        "difference_percentage_points": 100 * sum(differences) / len(differences),
        "bootstrap_ci95_percentage_points": [100 * boot[int(0.025 * bootstrap_samples)], 100 * boot[int(0.975 * bootstrap_samples)]],
        "mcnemar": mcnemar_exact(b_count, c_count),
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, (original, value) in enumerate(indexed):
        running = max(running, min(1.0, (m - rank) * value))
        adjusted[original] = running
    return adjusted


def weighted_kappa(pairs: list[tuple[int, int]], levels: int = 3) -> float | None:
    if not pairs:
        return None
    matrix = [[0 for _ in range(levels)] for _ in range(levels)]
    for a, b in pairs:
        matrix[a][b] += 1
    n = len(pairs)
    row = [sum(values) for values in matrix]
    col = [sum(matrix[i][j] for i in range(levels)) for j in range(levels)]
    observed = expected = 0.0
    denominator = max(1, (levels - 1) ** 2)
    for i in range(levels):
        for j in range(levels):
            weight = ((i - j) ** 2) / denominator
            observed += weight * matrix[i][j] / n
            expected += weight * row[i] * col[j] / (n * n)
    return 1.0 if expected == 0 and observed == 0 else (None if expected == 0 else 1 - observed / expected)


def confirmatory_report(rows: list[dict]) -> list[dict]:
    specifications = [
        ("grammar", "pivot_persian", "H1a"),
        ("factual", "pivot_russian", "H1b Russian"),
        ("factual", "pivot_english", "H1b English"),
    ]
    results = []
    models = sorted({row.get("model", "") for row in rows if row.get("model")})
    for model in models:
        for category, treatment, hypothesis in specifications:
            subset = [r for r in rows if r.get("model") == model and r.get("category") == category]
            result = paired_binary_comparison(subset, "direct_tajik", treatment)
            result.update({"model": model, "category": category, "hypothesis": hypothesis})
            if result.get("n_pairs"):
                results.append(result)
    adjusted = holm_adjust([r["mcnemar"]["p_value"] for r in results])
    for result, p_value in zip(results, adjusted):
        result["holm_adjusted_p_value"] = p_value
        result["practically_meaningful_5pp"] = abs(result["difference_percentage_points"]) >= 5
    return results
