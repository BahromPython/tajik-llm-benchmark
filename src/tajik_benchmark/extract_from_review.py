"""Extract items from HTML review interface and evaluate with council."""

import json
import re
from pathlib import Path
from .council_evaluator import evaluate_answer, export_to_json, export_to_csv


def extract_items_from_html(html_path: str) -> list:
    """Extract all items from Bahrom's HTML review file."""

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the REVIEW_PAYLOAD object in the HTML
    match = re.search(r'window\.REVIEW_PAYLOAD = (\{.*?\});', content, re.DOTALL)
    if not match:
        match = re.search(r'<script>window\.REVIEW_PAYLOAD = (\{.*?\});</script>', content, re.DOTALL)

    if not match:
        raise ValueError("Could not find REVIEW_PAYLOAD in HTML")

    payload_str = match.group(1)

    # Parse the JSON
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing payload: {e}")
        raise

    items = payload.get("assignments", [])
    print(f"✓ Extracted {len(items)} items from HTML")
    print(f"  Study: {payload.get('study_id')}")
    print(f"  Reviewer: {payload.get('reviewer_name')}")

    return items


def process_items_batch(
    items: list, output_file: str = "bahrom_council_eval", study_id: str = "bahrom-450"
) -> None:
    """
    Process all 450 items with council evaluator in BATCH mode.
    450 items × 1 prompt = 450 API calls (not 1,350)
    """

    all_records = []
    total = len(items)

    print(f"\n{'='*60}")
    print(f"Processing {total} items with BATCH mode (1 prompt per item)")
    print(f"API calls needed: ~{total} (not {total * 3})")
    print(f"{'='*60}\n")

    for idx, item in enumerate(items, 1):
        blind_id = item.get("blind_id", f"blind-{idx}")
        item_id = item.get("item_id", f"item-{idx}")
        question = item.get("task_prompt_tajik", "")
        answer = item.get("model_response", "")

        # Show progress
        if idx % 50 == 0 or idx == 1:
            print(f"[{idx}/{total}] Processing {blind_id}...")

        try:
            # BATCH MODE: ONE API call for all 3 evaluators
            result = evaluate_answer(
                answer=answer,
                question=question,
                item_id=item_id,
                blind_id=blind_id,
                study_id=study_id,
                batch_mode=True,  # KEY: Batch mode = 1 prompt for all 3
            )

            # Collect export records
            all_records.extend(result["export_records"])

        except Exception as e:
            print(f"  ⚠️  Error on item {idx}: {str(e)}")
            continue

    # Save results
    print(f"\n{'='*60}")
    print(f"✓ Processed {total} items")
    print(f"✓ Generated {len(all_records)} evaluation records")
    print(f"{'='*60}\n")

    # JSON export
    json_file = f"{output_file}.json"
    export_data = {
        "export_schema": "tajik-human-review-v1",
        "study_id": study_id,
        "assigned_count": total,
        "completed_count": total,
        "ratings": all_records,
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON export saved: {json_file}")

    # CSV export
    csv_file = f"{output_file}.csv"
    export_to_csv({"export_records": all_records}, csv_file)
    print(f"✓ CSV export saved: {csv_file}")

    print(f"\n📊 Summary:")
    print(f"   Items evaluated: {total}")
    print(f"   Total ratings: {len(all_records)} ({total} × 3 evaluators)")
    print(f"   API calls used: ~{total} (batch mode)")
    print(f"   Files generated: JSON, CSV")


def main():
    """Extract Bahrom's 450 items and evaluate with council."""

    html_path = "/root/.claude/uploads/f2cd2fd8-287c-5b14-8d9a-ea4effedaaa2/3b4647c6-Bahrom_Review.html"

    if not Path(html_path).exists():
        print(f"Error: {html_path} not found")
        return

    print("Extracting items from Bahrom's review HTML...")
    items = extract_items_from_html(html_path)

    print(f"\nStarting batch evaluation of {len(items)} items...")
    process_items_batch(items, output_file="bahrom_council_eval", study_id="bahrom-450")


if __name__ == "__main__":
    main()
