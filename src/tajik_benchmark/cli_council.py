#!/usr/bin/env python3
"""Command-line interface for the council evaluator."""

import argparse
import json
import sys
import csv
from pathlib import Path
from council_evaluator import evaluate_answer, format_report


def evaluate_single(args):
    """Evaluate a single answer."""
    print(f"Evaluating answer for question: {args.question}\n")

    result = evaluate_answer(
        answer=args.answer,
        question=args.question,
        expected_answer=args.expected_answer,
        context=args.context or ""
    )

    # Output
    if args.output_format == "text":
        print(format_report(result))
    elif args.output_format == "json":
        print(json.dumps(result, indent=2))

    # Save if specified
    if args.save:
        with open(args.save, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Results saved to {args.save}")


def evaluate_batch(args):
    """Evaluate multiple answers from a CSV file."""
    input_path = Path(args.input_csv)
    if not input_path.exists():
        print(f"Error: Input file {args.input_csv} not found", file=sys.stderr)
        sys.exit(1)

    results = []
    with open(input_path) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            print(f"[{i}] Evaluating: {row.get('question', 'N/A')[:50]}...")

            result = evaluate_answer(
                answer=row['answer'],
                question=row['question'],
                expected_answer=row.get('expected_answer'),
                context=row.get('context', '')
            )

            results.append({
                'id': row.get('id', i),
                'question': row['question'],
                'consensus_score': result.get('consensus', {}).get('consensus_score_0_to_10', 5),
                'overall_rating': result.get('overall_rating', 'Unknown'),
                'recommendation': result.get('consensus', {}).get('recommendation', ''),
                'full_result': result
            })

    # Save results
    output_path = Path(args.output_csv or "evaluation_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Evaluated {len(results)} answers")
    print(f"✓ Results saved to {output_path}")

    # Print summary
    if args.summary:
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        for result in results:
            print(f"ID: {result['id']} | Score: {result['consensus_score']}/10 | Rating: {result['overall_rating']}")


def main():
    parser = argparse.ArgumentParser(
        description="Tajik LLM Council Evaluator - Multi-personality evaluation system"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Single evaluation
    single_parser = subparsers.add_parser("eval", help="Evaluate a single answer")
    single_parser.add_argument("--answer", "-a", required=True, help="The answer to evaluate")
    single_parser.add_argument("--question", "-q", required=True, help="The original question")
    single_parser.add_argument("--expected", "-e", dest="expected_answer", help="Expected/reference answer")
    single_parser.add_argument("--context", "-c", help="Additional context")
    single_parser.add_argument("--format", dest="output_format", choices=["text", "json"], default="text", help="Output format")
    single_parser.add_argument("--save", "-s", help="Save results to JSON file")
    single_parser.set_defaults(func=evaluate_single)

    # Batch evaluation
    batch_parser = subparsers.add_parser("batch", help="Evaluate multiple answers from CSV")
    batch_parser.add_argument("--input", "-i", dest="input_csv", required=True, help="Input CSV file")
    batch_parser.add_argument("--output", "-o", dest="output_csv", help="Output JSON file")
    batch_parser.add_argument("--summary", action="store_true", help="Print summary after evaluation")
    batch_parser.set_defaults(func=evaluate_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
