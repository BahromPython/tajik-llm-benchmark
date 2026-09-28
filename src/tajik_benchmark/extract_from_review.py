"""Extract items from HTML review interface and evaluate with council."""

import json
import re
from pathlib import Path
from .council_evaluator import evaluate_answer, export_to_json, export_to_csv


def extract_items_from_html(html_path: str) -> tuple:
    """Extract all items and assignment metadata from Bahrom's HTML review file.

    Returns (items, metadata) where metadata carries study_id, dataset_sha256,
    assignment_version, reviewer_id, reviewer_name -- exactly as the HTML review
    interface's own exportJSON()/exportRows() embed them in every export.
    """

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
    metadata = {
        "study_id": payload.get("study_id", ""),
        "dataset_sha256": payload.get("dataset_sha256", ""),
        "assignment_version": payload.get("assignment_version", ""),
        "reviewer_id": payload.get("reviewer_id", ""),
        "reviewer_name": payload.get("reviewer_name", ""),
    }
    print(f"✓ Extracted {len(items)} items from HTML")
    print(f"  Study: {metadata['study_id']}")
    print(f"  Reviewer: {metadata['reviewer_name']}")

    return items, metadata


def process_items_batch(
    items: list,
    metadata: dict,
    output_file: str = "bahrom_council_eval",
) -> None:
    """
    Process all items with council evaluator in BATCH mode.
    N items x 1 prompt = N API calls (not 3N).

    `metadata` must carry study_id, dataset_sha256, assignment_version,
    reviewer_id, reviewer_name -- as returned by extract_items_from_html() --
    so every exported record matches the HTML review interface's own
    tajik-human-review-v1 schema exactly.
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
                study_id=metadata["study_id"],
                dataset_sha256=metadata["dataset_sha256"],
                assignment_version=metadata["assignment_version"],
                assignment_order=idx,
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

    complete_count = sum(1 for r in all_records if r["complete"])

    # JSON export -- matches the HTML review interface's exportJSON() exactly
    json_file = f"{output_file}.json"
    export_data = {
        "export_schema": "tajik-human-review-v1",
        "study_id": metadata["study_id"],
        "dataset_sha256": metadata["dataset_sha256"],
        "assignment_version": metadata["assignment_version"],
        "reviewer_id": metadata["reviewer_id"],
        "reviewer_name": metadata["reviewer_name"],
        "assigned_count": total,
        "completed_count": complete_count,
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
    print(f"   Total ratings: {len(all_records)} ({total} × 4 evaluators)")
    print(f"   API calls used: ~{total} (batch mode)")
    print(f"   Files generated: JSON, CSV")


def main():
    """Extract Bahrom's 450 items and evaluate with council."""

    html_path = "/root/.claude/uploads/f2cd2fd8-287c-5b14-8d9a-ea4effedaaa2/3b4647c6-Bahrom_Review.html"

    if not Path(html_path).exists():
        print(f"Error: {html_path} not found")
        return

    print("Extracting items from Bahrom's review HTML...")
    items, metadata = extract_items_from_html(html_path)

    print(f"\nStarting batch evaluation of {len(items)} items...")
    process_items_batch(items, metadata, output_file="bahrom_council_eval")


if __name__ == "__main__":
    main()
