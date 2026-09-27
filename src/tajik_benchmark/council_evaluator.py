"""
Multi-personality council evaluator using Gemini API.
Three distinct personas assess answers independently, then reason toward consensus.
"""

import os
import json
from typing import Optional
import requests

# Initialize Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


# Define three evaluator personas with distinct perspectives
EVALUATORS = {
    "strict_linguist": {
        "name": "Dr. Linguist (Strict Grammarian)",
        "personality": "You are a rigorous Tajik linguist. You prioritize grammatical accuracy, register appropriateness, and precise terminology. You are detail-oriented and unforgiving of linguistic errors.",
        "focus": ["grammaticality", "naturalness", "code_switching_violations"],
    },
    "pragmatist": {
        "name": "The Pragmatist (Task Completion)",
        "personality": "You are a practical evaluator focused on whether the answer solves the user's problem. You value clarity, completeness, and task adherence over perfect grammar. You understand that slightly awkward phrasing is acceptable if meaning is clear.",
        "focus": ["instruction_adherence", "meaning_or_factual_correctness", "task_completion"],
    },
    "native_judge": {
        "name": "The Native Speaker (Authenticity)",
        "personality": "You are a native Tajik speaker evaluating whether the response sounds natural and idiomatic to a fluent ear. You assess fluency, register fit, and whether it reads like authentic Tajik or translated text.",
        "focus": ["naturalness", "fluency", "authenticity", "cultural_fit"],
    },
}

RUBRIC = {
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
    "meaning_or_factual_correctness": {
        "0": "Central meaning is wrong, missing, or factually incorrect.",
        "1": "Core answer is partly correct but incomplete or contains a minor substantive error.",
        "2": "Core meaning and relevant facts are correct.",
    },
    "instruction_adherence": {
        "0": "Does not complete the requested task or violates the required format substantially.",
        "1": "Completes the main task but misses a secondary instruction or format constraint.",
        "2": "Follows the task, language, register, length, and format instructions.",
    },
}


def evaluate_answer(
    answer: str, question: str, expected_answer: Optional[str] = None, context: str = ""
) -> dict:
    """
    Evaluate an answer using the three-personality council.

    Args:
        answer: The response to evaluate
        question: The original question/task
        expected_answer: Optional reference/expected answer
        context: Additional context about the task

    Returns:
        Dictionary with individual evaluations and consensus scores
    """

    evaluations = {}
    reasoning = {}

    # Step 1: Get individual evaluations from each persona
    for persona_id, persona_info in EVALUATORS.items():
        evaluation = _get_persona_evaluation(
            persona_id, persona_info, answer, question, expected_answer, context
        )
        evaluations[persona_id] = evaluation
        reasoning[persona_id] = evaluation.get("reasoning", "")

    # Step 2: Generate discussion/consensus
    consensus = _generate_consensus(evaluations, question, answer)

    # Step 3: Aggregate scores
    final_scores = _aggregate_scores(evaluations)

    return {
        "individual_evaluations": evaluations,
        "reasoning_by_persona": reasoning,
        "consensus": consensus,
        "final_scores": final_scores,
        "overall_rating": _calculate_overall_rating(final_scores),
    }


def _get_persona_evaluation(
    persona_id: str,
    persona_info: dict,
    answer: str,
    question: str,
    expected_answer: Optional[str],
    context: str,
) -> dict:
    """Get evaluation from a single persona using Gemini REST API."""

    prompt = f"""
{persona_info['personality']}

You are evaluating a Tajik language response. Use this rubric:

GRAMMATICALITY:
0: Major grammatical errors make the response incorrect or difficult to understand.
1: Meaning is understandable, but one or more noticeable grammatical problems remain.
2: Grammatically acceptable Tajik for the requested register.

NATURALNESS:
0: Clearly unnatural, translated, or non-Tajik phrasing dominates.
1: Mostly understandable but contains awkward or non-idiomatic phrasing.
2: Natural Tajik phrasing appropriate for the task and register.

MEANING/FACTUAL CORRECTNESS:
0: Central meaning is wrong, missing, or factually incorrect.
1: Core answer is partly correct but incomplete or contains a minor substantive error.
2: Core meaning and relevant facts are correct.

INSTRUCTION ADHERENCE:
0: Does not complete the requested task or violates the required format substantially.
1: Completes the main task but misses a secondary instruction or format constraint.
2: Follows the task, language, register, length, and format instructions.

CODE-SWITCHING VIOLATIONS (count unjustified Russian/English when Tajik equivalent exists):
0: No unnecessary code-switching
1-2: Minor code-switching issues
3+: Significant code-switching problems

TASK CONTEXT:
Question: {question}
{f"Expected/Reference Answer: {expected_answer}" if expected_answer else ""}
{f"Additional Context: {context}" if context else ""}

RESPONSE TO EVALUATE:
{answer}

Provide your evaluation in JSON format with the following structure:
{{
    "grammaticality_score": <0-2>,
    "naturalness_score": <0-2>,
    "meaning_correctness_score": <0-2>,
    "instruction_adherence_score": <0-2>,
    "code_switching_violations": <count>,
    "reasoning": "<Your detailed assessment explaining each score>",
    "strengths": ["<strength1>", "<strength2>"],
    "weaknesses": ["<weakness1>", "<weakness2>"],
    "recommendation": "<Overall assessment>"
}}
"""

    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        url = f"{GEMINI_API_URL}?key={API_KEY}"

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        text_response = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        # Extract JSON from response
        try:
            result = json.loads(text_response)
        except json.JSONDecodeError:
            # Try to extract JSON if wrapped in markdown
            if "```json" in text_response:
                json_str = text_response.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_str)
            else:
                raise

        return result
    except (json.JSONDecodeError, requests.RequestException, KeyError) as e:
        return {
            "error": f"Failed to evaluate: {str(e)}",
            "grammaticality_score": 0,
            "naturalness_score": 0,
            "meaning_correctness_score": 0,
            "instruction_adherence_score": 0,
            "code_switching_violations": 0,
            "reasoning": f"Error: {str(e)}",
        }


def _generate_consensus(evaluations: dict, question: str, answer: str) -> dict:
    """Generate consensus/discussion between the three evaluators."""

    evaluations_summary = json.dumps(evaluations, indent=2)

    prompt = f"""
You are moderating a discussion between three expert evaluators of Tajik language responses:

1. Dr. Linguist (Strict Grammarian) - focuses on grammar and linguistic precision
2. The Pragmatist (Task Completion) - focuses on whether the task is completed
3. The Native Speaker (Authenticity) - focuses on whether it sounds natural to a fluent ear

THEIR EVALUATIONS:
{evaluations_summary}

ORIGINAL QUESTION:
{question}

RESPONSE EVALUATED:
{answer}

Based on their individual assessments, summarize:
1. **Points of Agreement**: Where do all three evaluators agree?
2. **Points of Disagreement**: Where do they differ, and why?
3. **Critical Issues**: Are there any deal-breaker problems?
4. **Consensus Score**: What is the fair overall assessment (0-10 scale)?
5. **Final Recommendation**: Is this response acceptable? What improvements are needed?

Provide your consensus as JSON:
{{
    "points_of_agreement": ["<agreement1>", "<agreement2>"],
    "points_of_disagreement": {{"issue": "<disagreement explanation>"}},
    "critical_issues": ["<issue1>", "<issue2>"],
    "consensus_score_0_to_10": <0-10>,
    "recommendation": "<Final verdict>",
    "improvements_needed": ["<improvement1>", "<improvement2>"]
}}
"""

    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        url = f"{GEMINI_API_URL}?key={API_KEY}"

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        text_response = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        try:
            result = json.loads(text_response)
        except json.JSONDecodeError:
            if "```json" in text_response:
                json_str = text_response.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_str)
            else:
                raise

        return result
    except (json.JSONDecodeError, requests.RequestException, KeyError) as e:
        return {
            "error": f"Failed to generate consensus: {str(e)}",
            "consensus_score_0_to_10": 5,
            "recommendation": "Unable to generate consensus",
        }


def _aggregate_scores(evaluations: dict) -> dict:
    """Calculate average scores across all evaluators."""

    dimensions = [
        "grammaticality_score",
        "naturalness_score",
        "meaning_correctness_score",
        "instruction_adherence_score",
    ]

    aggregated = {}

    for dimension in dimensions:
        scores = []
        for persona_id, evaluation in evaluations.items():
            if dimension in evaluation and isinstance(evaluation[dimension], (int, float)):
                scores.append(evaluation[dimension])

        if scores:
            aggregated[dimension] = {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "individual_scores": {
                    persona_id: evaluations[persona_id].get(dimension, None)
                    for persona_id in evaluations
                },
            }

    return aggregated


def _calculate_overall_rating(final_scores: dict) -> str:
    """Calculate overall rating based on average scores."""

    if not final_scores:
        return "Unable to calculate"

    averages = [s["average"] for s in final_scores.values() if "average" in s]

    if not averages:
        return "Unable to calculate"

    overall_avg = sum(averages) / len(averages)

    if overall_avg >= 1.8:
        return "EXCELLENT (1.8-2.0)"
    elif overall_avg >= 1.5:
        return "GOOD (1.5-1.8)"
    elif overall_avg >= 1.0:
        return "ACCEPTABLE (1.0-1.5)"
    else:
        return "NEEDS IMPROVEMENT (<1.0)"


def format_report(evaluation_result: dict) -> str:
    """Format the evaluation result as a readable report."""

    report = []
    report.append("=" * 80)
    report.append("TAJIK LLM ANSWER EVALUATION - COUNCIL OF THREE")
    report.append("=" * 80)

    # Individual Evaluations
    report.append("\n📋 INDIVIDUAL EVALUATIONS\n")

    for persona_id, eval_result in evaluation_result["individual_evaluations"].items():
        persona_name = EVALUATORS[persona_id]["name"]
        report.append(f"\n{persona_name}:")
        report.append("-" * 40)

        for dimension in [
            "grammaticality_score",
            "naturalness_score",
            "meaning_correctness_score",
            "instruction_adherence_score",
        ]:
            if dimension in eval_result:
                score = eval_result[dimension]
                report.append(f"  • {dimension.replace('_score', '').title()}: {score}/2")

        if "code_switching_violations" in eval_result:
            report.append(f"  • Code-switching violations: {eval_result['code_switching_violations']}")

        if "reasoning" in eval_result:
            report.append(f"\n  Reasoning: {eval_result['reasoning'][:200]}...")

    # Consensus
    report.append("\n\n🤝 COUNCIL CONSENSUS\n")
    consensus = evaluation_result.get("consensus", {})

    if "points_of_agreement" in consensus:
        report.append("Agreement Points:")
        for point in consensus["points_of_agreement"]:
            report.append(f"  ✓ {point}")

    if "critical_issues" in consensus:
        report.append("\nCritical Issues:")
        for issue in consensus["critical_issues"]:
            report.append(f"  ⚠️ {issue}")

    if "consensus_score_0_to_10" in consensus:
        report.append(
            f"\nConsensus Score: {consensus['consensus_score_0_to_10']}/10"
        )

    if "recommendation" in consensus:
        report.append(f"\nRecommendation: {consensus['recommendation']}")

    # Final Scores
    report.append("\n\n📊 FINAL AGGREGATED SCORES\n")
    for dimension, scores in evaluation_result.get("final_scores", {}).items():
        if isinstance(scores, dict) and "average" in scores:
            report.append(
                f"{dimension.replace('_score', '').title()}: {scores['average']:.2f}/2.0 (range: {scores['min']}-{scores['max']})"
            )

    # Overall Rating
    report.append(f"\n⭐ Overall Rating: {evaluation_result.get('overall_rating', 'N/A')}\n")

    report.append("=" * 80)

    return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    test_answer = "Салом! Ман хуб аст."
    test_question = "Чӣ хол доро ва чӣ кор мекунед?"

    print("Starting council evaluation...")
    result = evaluate_answer(test_answer, test_question, context="Conversational greeting")
    print(format_report(result))
