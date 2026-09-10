from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from .io import iter_jsonl, load_items, read_json, write_json, write_jsonl
from .audit import audit_items, stratified_review_sample
from .planning import build_plan
from .providers import get_provider
from .runner import run_plan
from .dashboard import build_dashboard
from .inference import confirmatory_report
from .scoring import response_quality_flags, score_objective
from .statistics import summarize_accuracy, summarize_efficiency
from .validation import assert_no_overlap, validate_items


def cmd_validate(args):
    items = load_items(args.items)
    errors = validate_items(items)
    if not errors:
        assert_no_overlap(items)
        print(f"OK: {len(items)} items validated")
        return 0
    for error in errors:
        print(f"ERROR: {error}")
    return 1


def cmd_audit(args):
    items = load_items(args.items)
    report = audit_items(items, near_duplicate_threshold=args.threshold)
    write_json(args.output, report)
    print(
        f"Audited {report['item_count']} items: {len(report['exact_duplicate_groups'])} exact duplicate groups, "
        f"{len(report['near_duplicate_pairs'])} near-duplicate pairs"
    )
    return 0


def cmd_sample_review(args):
    rows = stratified_review_sample(load_items(args.items), args.per_cell, args.seed)
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No review rows selected")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    print(f"Wrote {len(rows)} stratified professor-review items to {output}")
    return 0


def cmd_plan(args):
    items = load_items(args.items)
    errors = validate_items(items)
    if errors:
        raise ValueError("Dataset validation failed:\n" + "\n".join(errors))
    assert_no_overlap(items)
    requests = build_plan(items, read_json(args.config), unlock_test=args.unlock_test)
    write_jsonl(args.output, (request.to_dict() for request in requests))
    print(f"Wrote {len(requests)} planned requests to {args.output}")
    return 0


def cmd_run_mock(args):
    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite raw responses: {output}")
    records = []
    for request in iter_jsonl(args.plan):
        provider = get_provider(request["model"]["provider"])
        started = datetime.now(timezone.utc)
        timer = time.perf_counter()
        result = provider.generate(request)
        latency_ms = round((time.perf_counter() - timer) * 1000, 3)
        records.append(
            {
                **request,
                "response_id": request["request_id"],
                "response_text": result.text,
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "started_at_utc": started.isoformat(),
                "latency_ms": latency_ms,
                "retry_count": 0,
                "request_status": "ok",
                "usage": result.usage,
                "provider_metadata": result.provider_metadata,
            }
        )
    write_jsonl(output, records)
    print(f"Wrote {len(records)} raw responses to {output}")
    return 0


def cmd_run(args):
    summary = run_plan(
        args.plan, args.output, read_json(args.pricing), resume=args.resume,
        max_requests=args.max_requests, max_cost_usd=args.max_cost_usd,
        max_retries=args.max_retries,
    )
    print(f"Run finished: {summary['succeeded']} succeeded, {summary['failed']} failed, "
          f"estimated cost ${summary['estimated_cost_usd']:.6f}")
    return 0 if summary["failed"] == 0 else 2


def cmd_score(args):
    item_map = {item.item_id: item.to_dict() for item in load_items(args.items)}
    fieldnames = [
        "response_id", "item_id", "split", "category", "subtype", "model", "provider",
        "condition", "repetition", "prediction", "objective_correct", "response_text",
        "input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens", "total_tokens",
        "token_source", "estimated_cost_usd", "latency_ms", "retry_count", "request_status",
        "response_words", "response_characters", "format_violation", "empty_response",
    ]
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames); writer.writeheader()
        count = 0
        for record in iter_jsonl(args.responses):
            item = item_map[record["item"]["item_id"]]
            prediction, correct = score_objective(item, record["response_text"])
            flags = response_quality_flags(item, record["response_text"])
            usage = record.get("usage") or {}
            writer.writerow(
                {
                    "response_id": record["response_id"], "item_id": item["item_id"],
                    "split": item["split"], "category": item["category"], "subtype": item["subtype"],
                    "model": record["model"]["model"], "provider": record["model"]["provider"],
                    "condition": record["condition"], "repetition": record["repetition"],
                    "prediction": prediction, "objective_correct": "" if correct is None else correct,
                    "response_text": record["response_text"],
                    "input_tokens": usage.get("input_tokens", ""),
                    "output_tokens": usage.get("output_tokens", ""),
                    "cached_tokens": usage.get("cached_tokens", ""),
                    "reasoning_tokens": usage.get("reasoning_tokens", ""),
                    "total_tokens": usage.get("total_tokens", ""),
                    "token_source": usage.get("token_source", "unavailable"),
                    "estimated_cost_usd": record.get("estimated_cost_usd", ""),
                    "latency_ms": record.get("latency_ms", ""),
                    "retry_count": record.get("retry_count", 0),
                    "request_status": record.get("request_status", "ok"),
                    **flags,
                }
            ); count += 1
    print(f"Wrote {count} scored responses to {output}")
    return 0


def cmd_analyze(args):
    with Path(args.scores).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    summary = {
        "source": str(args.scores),
        "accuracy_groups": summarize_accuracy(rows),
        "efficiency_groups": summarize_efficiency(rows),
        "confirmatory_paired_comparisons": confirmatory_report(rows),
    }
    write_json(args.output, summary)
    print(f"Wrote analysis summary to {args.output}")
    return 0


def cmd_dashboard(args):
    build_dashboard(args.scores, args.output, args.title)
    print(f"Wrote privacy-safe professor dashboard to {args.output}")
    return 0


def parser():
    p = argparse.ArgumentParser(prog="tajik-bench")
    commands = p.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate"); validate.add_argument("--items", required=True); validate.set_defaults(func=cmd_validate)
    audit = commands.add_parser("audit"); audit.add_argument("--items", required=True); audit.add_argument("--output", required=True); audit.add_argument("--threshold", type=float, default=0.82); audit.set_defaults(func=cmd_audit)
    review = commands.add_parser("sample-review"); review.add_argument("--items", required=True); review.add_argument("--output", required=True); review.add_argument("--per-cell", type=int, default=3); review.add_argument("--seed", type=int, default=20260819); review.set_defaults(func=cmd_sample_review)
    plan = commands.add_parser("plan"); plan.add_argument("--items", required=True); plan.add_argument("--config", required=True); plan.add_argument("--output", required=True); plan.add_argument("--unlock-test", action="store_true"); plan.set_defaults(func=cmd_plan)
    run = commands.add_parser("run-mock"); run.add_argument("--plan", required=True); run.add_argument("--output", required=True); run.add_argument("--overwrite", action="store_true"); run.set_defaults(func=cmd_run_mock)
    real = commands.add_parser("run"); real.add_argument("--plan", required=True); real.add_argument("--output", required=True); real.add_argument("--pricing", required=True); real.add_argument("--resume", action="store_true"); real.add_argument("--max-requests", type=int); real.add_argument("--max-cost-usd", type=float); real.add_argument("--max-retries", type=int, default=5); real.set_defaults(func=cmd_run)
    score = commands.add_parser("score"); score.add_argument("--items", required=True); score.add_argument("--responses", required=True); score.add_argument("--output", required=True); score.set_defaults(func=cmd_score)
    analyze = commands.add_parser("analyze"); analyze.add_argument("--scores", required=True); analyze.add_argument("--output", required=True); analyze.set_defaults(func=cmd_analyze)
    dashboard = commands.add_parser("dashboard"); dashboard.add_argument("--scores", required=True); dashboard.add_argument("--output", required=True); dashboard.add_argument("--title", default="Tajik LLM Benchmark Results"); dashboard.set_defaults(func=cmd_dashboard)
    return p


def main():
    args = parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
