#!/usr/bin/env python3
"""CLI for council evaluator - exports in tajik-human-review-v1 schema."""

import argparse
import json
import sys
import csv
from pathlib import Path
from council_evaluator import (
    evaluate_answer,
    export_to_json,
    export_to_csv,
    generate_html_report,
)


def evaluate_single(args):
    """Evaluate a single answer and export in all formats."""

    result = evaluate_answer(
        answer=args.answer,
        question=args.question,
        expected_answer=args.expected_answer,
        context=args.context or "",
        item_id=args.item_id or "",
        blind_id=args.blind_id or "",
        study_id=args.study_id or "council-eval",
        reviewer_name="AI Council",
    )

    # Default output file
    base_name = args.output or f"evaluation_{args.blind_id or 'result'}"

    # Export JSON (export schema)
    json_file = f"{base_name}.json"
    export_to_json(result, json_file)
    print(f"✓ JSON export: {json_file}")

    # Export CSV (export schema)
    csv_file = f"{base_name}.csv"
    export_to_csv(result, csv_file)
    print(f"✓ CSV export: {csv_file}")

    # Export HTML report
    html_file = f"{base_name}_report.html"
    html_content = generate_html_report(result)
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✓ HTML report: {html_file}")

    # Print summary
    print(f"\nEvaluation complete!")
    print(f"Records: {len(result['export_records'])} evaluators")
    for record in result["export_records"]:
        print(f"  - {record['reviewer_name']}")


def evaluate_batch(args):
    """Evaluate multiple answers from CSV file."""

    input_path = Path(args.input_csv)
    if not input_path.exists():
        print(f"Error: Input file {args.input_csv} not found", file=sys.stderr)
        sys.exit(1)

    all_records = []
    study_id = args.study_id or "council-batch"

    with open(input_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            print(f"[{i}] Evaluating: {row.get('question', 'N/A')[:50]}...")

            result = evaluate_answer(
                answer=row["answer"],
                question=row["question"],
                expected_answer=row.get("expected_answer"),
                context=row.get("context", ""),
                item_id=row.get("item_id", f"item-{i}"),
                blind_id=row.get("blind_id", f"blind-{i}"),
                study_id=study_id,
                reviewer_name="AI Council",
            )

            # Collect all export records
            all_records.extend(result["export_records"])

    # Save combined results
    output_file = args.output or f"{study_id}_evaluations"

    # JSON export
    json_file = f"{output_file}.json"
    export_data = {
        "export_schema": "tajik-human-review-v1",
        "study_id": study_id,
        "assigned_count": len(all_records) // 3,  # 3 evaluators per assignment
        "completed_count": len(all_records) // 3,
        "ratings": all_records,
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ JSON export: {json_file}")

    # CSV export
    csv_file = f"{output_file}.csv"
    fieldnames = list(all_records[0].keys()) if all_records else []
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)
    print(f"✓ CSV export: {csv_file}")

    print(
        f"\nBatch complete! Evaluated {len(all_records) // 3} answers with {len(all_records)} ratings."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Tajik Council Evaluator - Export in tajik-human-review-v1 schema"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Single evaluation
    single_parser = subparsers.add_parser(
        "eval", help="Evaluate a single answer (exports JSON/CSV/HTML)"
    )
    single_parser.add_argument("--answer", "-a", required=True, help="Answer to evaluate")
    single_parser.add_argument("--question", "-q", required=True, help="Original question")
    single_parser.add_argument("--expected", "-e", dest="expected_answer", help="Reference answer")
    single_parser.add_argument("--context", "-c", help="Additional context")
    single_parser.add_argument("--item-id", help="Item ID for export schema")
    single_parser.add_argument("--blind-id", help="Blind ID for export schema")
    single_parser.add_argument("--study-id", help="Study ID (default: council-eval)")
    single_parser.add_argument("--output", "-o", help="Output file base name")
    single_parser.set_defaults(func=evaluate_single)

    # Batch evaluation
    batch_parser = subparsers.add_parser(
        "batch", help="Evaluate multiple answers from CSV (exports JSON/CSV)"
    )
    batch_parser.add_argument("--input", "-i", dest="input_csv", required=True, help="Input CSV")
    batch_parser.add_argument("--output", "-o", help="Output file base name")
    batch_parser.add_argument("--study-id", help="Study ID")
    batch_parser.set_defaults(func=evaluate_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
