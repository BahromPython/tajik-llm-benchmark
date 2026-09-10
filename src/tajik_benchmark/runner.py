from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from .io import iter_jsonl
from .providers import ProviderHTTPError, get_provider


def estimate_cost(usage: dict, model_id: str, pricing: dict) -> float | None:
    rates = pricing.get("models", {}).get(model_id)
    if not rates or usage.get("input_tokens") is None or usage.get("output_tokens") is None:
        return None
    cached = usage.get("cached_tokens") or 0
    uncached_input = max(0, usage["input_tokens"] - cached)
    cost = uncached_input * rates["input_per_million"] / 1_000_000
    cost += cached * rates.get("cached_input_per_million", rates["input_per_million"]) / 1_000_000
    cost += usage["output_tokens"] * rates["output_per_million"] / 1_000_000
    return round(cost, 10)


def _completed_ids(output: Path) -> set[str]:
    if not output.exists():
        return set()
    return {row["request_id"] for row in iter_jsonl(output) if row.get("request_status") == "ok"}


def run_plan(plan_path: str, output_path: str, pricing: dict, resume: bool = False,
             max_requests: int | None = None, max_cost_usd: float | None = None,
             max_retries: int = 5) -> dict:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not resume:
        raise FileExistsError(f"Refusing to overwrite {output}; use --resume or choose a new run file")
    completed = _completed_ids(output) if resume else set()
    mode = "a" if resume else "x"
    attempted = succeeded = failed = skipped = 0
    spent = 0.0
    started = datetime.now(timezone.utc).isoformat()
    with output.open(mode, encoding="utf-8", newline="\n") as handle:
        for request in iter_jsonl(plan_path):
            if request["request_id"] in completed:
                skipped += 1
                continue
            if max_requests is not None and attempted >= max_requests:
                break
            if max_cost_usd is not None and spent >= max_cost_usd:
                break
            attempted += 1
            provider = get_provider(request["model"]["provider"])
            attempt = 0
            error = None
            result = None
            timer = time.perf_counter()
            request_started = datetime.now(timezone.utc).isoformat()
            while attempt <= max_retries:
                try:
                    result = provider.generate(request)
                    break
                except ProviderHTTPError as exc:
                    error = {"type": type(exc).__name__, "status": exc.status, "message": str(exc)[:2000], "retryable": exc.retryable}
                    if not exc.retryable or attempt == max_retries:
                        break
                except Exception as exc:  # credential/configuration errors are recorded and not retried
                    error = {"type": type(exc).__name__, "status": None, "message": str(exc)[:2000], "retryable": False}
                    break
                delay = min(60.0, (2 ** attempt) + random.random())
                time.sleep(delay)
                attempt += 1
            latency_ms = round((time.perf_counter() - timer) * 1000, 3)
            if result is not None:
                cost = estimate_cost(result.usage, request["model"]["model"], pricing)
                if cost is not None:
                    spent += cost
                record = {**request, "response_id": request["request_id"], "response_text": result.text,
                          "started_at_utc": request_started, "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                          "latency_ms": latency_ms, "retry_count": attempt, "request_status": "ok",
                          "usage": result.usage, "estimated_cost_usd": cost,
                          "pricing_snapshot_date": pricing.get("snapshot_date"), "provider_metadata": result.provider_metadata}
                succeeded += 1
            else:
                record = {**request, "response_id": request["request_id"], "response_text": "",
                          "started_at_utc": request_started, "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                          "latency_ms": latency_ms, "retry_count": attempt, "request_status": "failed",
                          "usage": {}, "estimated_cost_usd": None, "pricing_snapshot_date": pricing.get("snapshot_date"),
                          "provider_metadata": {}, "error": error}
                failed += 1
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "attempted": attempted, "succeeded": succeeded, "failed": failed, "skipped_completed": skipped,
            "estimated_cost_usd": round(spent, 6), "output": str(output)}
