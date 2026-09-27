"""
Multi-personality council evaluator using Gemini API.
Three evaluators (Linguist, Pragmatist, Native Speaker) independently assess answers.
Exports results in tajik-human-review-v1 schema (matching HTML review interface).
"""

import os
import json
from typing import Optional
from datetime import datetime
import requests
import csv
from io import StringIO

# Initialize Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Three evaluator personas
EVALUATORS = {
    "linguist": {
        "name": "Dr. Linguist",
        "id": "dr-linguist",
        "personality": "You are a rigorous Tajik linguist. You prioritize grammatical accuracy, register appropriateness, and natural phrasing.",
    },
    "pragmatist": {
        "name": "Pragmatist",
        "id": "pragmatist",
        "personality": "You are a practical evaluator focused on task completion. You value clarity and whether the answer solves the user's problem.",
    },
    "native": {
        "name": "Native Speaker",
        "id": "native-speaker",
        "personality": "You are a native Tajik speaker evaluating authenticity. You assess whether it sounds natural and idiomatic to a fluent ear.",
    },
}

# Official rubric dimensions (5 of them)
RUBRIC_DIMENSIONS = [
    "grammaticality",
    "naturalness",
    "meaning_correctness",
    "instruction_adherence",
    "register_fit",
]

RUBRIC_DESCRIPTIONS = {
    "grammaticality": {
        "0": "Major grammatical errors make the response incorrect or difficult to understand.",
        "1": "Meaning is understandable, but one or more noticeable grammatical problems remain.",
        "2": "Grammatically acceptable Tajik for the requested register.",
    },
    "naturalness": {
        "0": "Clearly unnatural, translated, or non-Tajik phrasing dominates.",
        "1": "Mostly understandable but contains awkward or non-idiomatic phrasing.",
        "2": "Natural Tajik phrasing appropriate for the task and register.",
    },
    "meaning_correctness": {
        "0": "Central meaning is wrong, missing, or factually incorrect.",
        "1": "Core answer is partly correct but incomplete or contains a minor substantive error.",
        "2": "Core meaning and relevant facts are correct.",
    },
    "instruction_adherence": {
        "0": "Does not complete the requested task or violates the required format substantially.",
        "1": "Completes the main task but misses a secondary instruction or format constraint.",
        "2": "Follows the task, language, register, length, and format instructions.",
    },
    "register_fit": {
        "0": "Register is inappropriate for the task (formal/informal mismatch).",
        "1": "Register is mostly appropriate but has occasional lapses.",
        "2": "Register is perfectly suited to the task and context.",
    },
}


def evaluate_answer(
    answer: str,
    question: str,
    expected_answer: Optional[str] = None,
    context: str = "",
    item_id: str = "",
    blind_id: str = "",
    study_id: str = "council-eval",
    reviewer_name: str = "AI Council",
) -> dict:
    """
    Evaluate answer using three independent evaluators.
    Returns data in tajik-human-review-v1 export schema.
    """

    evaluations = {}

    # Get independent evaluations from each persona
    for persona_key, persona_info in EVALUATORS.items():
        eval_result = _get_persona_evaluation(
            persona_info, answer, question, expected_answer, context
        )
        evaluations[persona_key] = eval_result

    # Build export schema records (one per evaluator)
    export_records = []
    for persona_key, eval_result in evaluations.items():
        record = {
            "study_id": study_id,
            "reviewer_id": EVALUATORS[persona_key]["id"],
            "reviewer_name": EVALUATORS[persona_key]["name"],
            "blind_id": blind_id or f"response-{len(export_records)+1}",
            "item_id": item_id or "",
            "grammaticality": eval_result.get("grammaticality", ""),
            "naturalness": eval_result.get("naturalness", ""),
            "meaning_correctness": eval_result.get("meaning_correctness", ""),
            "instruction_adherence": eval_result.get("instruction_adherence", ""),
            "register_fit": eval_result.get("register_fit", ""),
            "unwanted_code_switching": eval_result.get("unwanted_code_switching", ""),
            "notes": eval_result.get("notes", ""),
            "flagged": False,
            "complete": all(
                eval_result.get(dim) != "" for dim in RUBRIC_DIMENSIONS
            )
            and eval_result.get("unwanted_code_switching") != "",
            "updated_at_utc": datetime.utcnow().isoformat() + "Z",
        }
        export_records.append(record)

    # Calculate consensus scores (average across evaluators)
    consensus_scores = _calculate_consensus(evaluations)

    return {
        "evaluations": evaluations,
        "export_records": export_records,
        "consensus_scores": consensus_scores,
        "question": question,
        "answer": answer,
    }


def _get_persona_evaluation(
    persona_info: dict, answer: str, question: str, expected_answer: Optional[str], context: str
) -> dict:
    """Get independent evaluation from one persona using Gemini."""

    dimensions_str = "\n".join(
        [
            f"{dim.upper()}:\n"
            + "\n".join(f"  {i}: {RUBRIC_DESCRIPTIONS[dim][str(i)]}" for i in range(3))
            for dim in RUBRIC_DIMENSIONS
        ]
    )

    prompt = f"""
{persona_info['personality']}

Score each dimension independently using the rubric below. Use only 0, 1, or 2.

{dimensions_str}

UNWANTED CODE-SWITCHING:
Answer: "yes" (unjustified Russian/English present), "no" (none), or "unclear"

TASK:
Question: {question}
{f"Context: {context}" if context else ""}
{f"Reference Answer: {expected_answer}" if expected_answer else ""}

RESPONSE TO EVALUATE:
{answer}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
    "grammaticality": <0-2>,
    "naturalness": <0-2>,
    "meaning_correctness": <0-2>,
    "instruction_adherence": <0-2>,
    "register_fit": <0-2>,
    "unwanted_code_switching": "<yes|no|unclear>",
    "notes": "<Brief explanation of your scores>"
}}
"""

    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        url = f"{GEMINI_API_URL}?key={API_KEY}"

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        text_response = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        # Extract JSON
        try:
            result = json.loads(text_response)
        except json.JSONDecodeError:
            if "```json" in text_response:
                json_str = text_response.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_str)
            elif "```" in text_response:
                json_str = text_response.split("```")[1].strip()
                result = json.loads(json_str)
            else:
                raise

        return result

    except (json.JSONDecodeError, requests.RequestException, KeyError) as e:
        return {
            "grammaticality": "",
            "naturalness": "",
            "meaning_correctness": "",
            "instruction_adherence": "",
            "register_fit": "",
            "unwanted_code_switching": "unclear",
            "notes": f"Error: {str(e)}",
        }


def _calculate_consensus(evaluations: dict) -> dict:
    """Calculate average scores across evaluators."""

    consensus = {}

    for dimension in RUBRIC_DIMENSIONS:
        scores = []
        for eval_result in evaluations.values():
            score = eval_result.get(dimension)
            if isinstance(score, (int, float)):
                scores.append(score)

        if scores:
            consensus[dimension] = {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
            }

    return consensus


def export_to_json(evaluation_result: dict, filename: str = None) -> str:
    """Export in tajik-human-review-v1 JSON schema."""

    export_data = {
        "export_schema": "tajik-human-review-v1",
        "study_id": evaluation_result["export_records"][0].get("study_id"),
        "assigned_count": 1,
        "completed_count": 1,
        "ratings": evaluation_result["export_records"],
    }

    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

    if filename:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json_str)

    return json_str


def export_to_csv(evaluation_result: dict, filename: str = None) -> str:
    """Export in tajik-human-review-v1 CSV schema."""

    records = evaluation_result["export_records"]

    if not records:
        return ""

    # CSV headers (matching the review interface)
    fieldnames = [
        "study_id",
        "reviewer_id",
        "reviewer_name",
        "blind_id",
        "item_id",
        "grammaticality",
        "naturalness",
        "meaning_correctness",
        "instruction_adherence",
        "register_fit",
        "unwanted_code_switching",
        "notes",
        "flagged",
        "complete",
        "updated_at_utc",
    ]

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for record in records:
        writer.writerow({k: record.get(k, "") for k in fieldnames})

    csv_str = output.getvalue()

    if filename:
        with open(filename, "w", encoding="utf-8-sig") as f:
            f.write(csv_str)

    return csv_str


def generate_html_report(evaluation_result: dict) -> str:
    """Generate HTML report showing all three evaluators' assessments."""

    evaluations = evaluation_result["evaluations"]
    consensus = evaluation_result["consensus_scores"]
    question = evaluation_result["question"]
    answer = evaluation_result["answer"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Council Evaluation Report</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }}
        .evaluator {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }}
        .evaluator h3 {{ color: #2980b9; margin-bottom: 15px; }}
        .scores-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        .score-card {{
            padding: 15px;
            background: white;
            border-radius: 4px;
            border: 1px solid #ecf0f1;
        }}
        .score-card .label {{
            font-weight: 600;
            color: #2c3e50;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .score {{
            font-size: 2em;
            font-weight: bold;
            color: #27ae60;
            text-align: center;
        }}
        .score.low {{ color: #e74c3c; }}
        .score.medium {{ color: #f39c12; }}
        .consensus {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 4px;
            margin-top: 20px;
        }}
        .consensus h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        .consensus-item {{
            margin-bottom: 10px;
            padding: 10px;
            background: white;
            border-radius: 3px;
        }}
        .consensus-item .dimension {{
            font-weight: 600;
            color: #2980b9;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .consensus-value {{
            font-size: 1.2em;
        }}
        .notes {{
            margin-top: 15px;
            padding: 15px;
            background: #fffacd;
            border-left: 3px solid #f39c12;
            border-radius: 3px;
            font-style: italic;
            color: #666;
        }}
        .export-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .export-buttons button {{
            padding: 10px 20px;
            background: #27ae60;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
        }}
        .export-buttons button:hover {{
            background: #229954;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Council Evaluation Report</h1>
            <p>Three independent evaluators assess the response</p>
        </div>

        <div class="section">
            <h2>Question</h2>
            <p style="padding: 15px; background: #f0f8ff; border-radius: 4px;">{question}</p>
        </div>

        <div class="section">
            <h2>Response Evaluated</h2>
            <p style="padding: 15px; background: #f0f8ff; border-radius: 4px;">{answer}</p>
        </div>

        <div class="section">
            <h2>📋 Individual Evaluations</h2>
"""

    for persona_key, persona_info in EVALUATORS.items():
        eval_data = evaluations.get(persona_key, {})

        html += f"""
            <div class="evaluator">
                <h3>{persona_info['name']}</h3>
                <div class="scores-grid">
"""

        for dimension in RUBRIC_DIMENSIONS:
            score = eval_data.get(dimension, "")
            score_class = "low" if score in [0] else "medium" if score in [1] else ""
            score_class = f"score {score_class}" if score_class else "score"

            html += f"""
                    <div class="score-card">
                        <div class="label">{dimension.replace('_', ' ')}</div>
                        <div class="{score_class}">{score}/2</div>
                    </div>
"""

        html += f"""
                </div>
                <div class="score-card">
                    <div class="label">Code Switching</div>
                    <div>{eval_data.get('unwanted_code_switching', '')}</div>
                </div>
"""

        if eval_data.get("notes"):
            html += f'<div class="notes"><strong>Notes:</strong> {eval_data.get("notes")}</div>'

        html += "</div>"

    html += f"""
        </div>

        <div class="section">
            <h2>🤝 Consensus Scores</h2>
            <div class="consensus">
"""

    for dimension in RUBRIC_DIMENSIONS:
        if dimension in consensus:
            avg = consensus[dimension]["average"]
            min_s = consensus[dimension]["min"]
            max_s = consensus[dimension]["max"]

            html += f"""
                <div class="consensus-item">
                    <div class="dimension">{dimension.replace('_', ' ')}</div>
                    <div class="consensus-value">
                        Average: <strong>{avg:.2f}</strong>/2.0 (range: {min_s}–{max_s})
                    </div>
                </div>
"""

    html += """
            </div>
        </div>
    </div>
</body>
</html>
"""

    return html


if __name__ == "__main__":
    test_answer = "Салом! Ман хуб аст ва кори занат дорам."
    test_question = "Чӣ хол доро ва чӣ кор мекунед?"

    print("Evaluating with council...")
    result = evaluate_answer(test_answer, test_question, context="Casual greeting")

    print("\n=== EXPORT RECORDS (JSON Schema) ===")
    print(export_to_json(result))

    print("\n=== CONSENSUS SCORES ===")
    print(json.dumps(result["consensus_scores"], indent=2))

    print("\nEvaluation complete!")
