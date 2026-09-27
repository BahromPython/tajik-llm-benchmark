# Tajik LLM Council Evaluator

A multi-personality evaluation system that uses **three distinct evaluator personas** to assess Tajik language responses using the professor-approved rubric.

## How It Works

The system creates a **council of three expert evaluators**, each with a unique perspective:

1. **Dr. Linguist (Strict Grammarian)** - Prioritizes grammatical accuracy, register appropriateness, and linguistic precision
2. **The Pragmatist (Task Completion)** - Focuses on whether the task is completed and meaning is clear
3. **The Native Speaker (Authenticity)** - Assesses naturalness, fluency, and whether it sounds like authentic Tajik

Each evaluator independently assesses the answer on **four criteria** (using the official rubric):
- **Grammaticality** (0-2): Correct syntax and grammar
- **Naturalness** (0-2): Natural, idiomatic Tajik phrasing
- **Meaning/Factual Correctness** (0-2): Core answer is correct
- **Instruction Adherence** (0-2): Task completed correctly

Plus **Code-Switching Analysis**: Count unjustified Russian/English when Tajik equivalents exist

## Setup

### 1. Get a Valid Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Create a new API key (free tier available)
3. Copy the key

### 2. Set Environment Variable

```bash
export GEMINI_API_KEY="your-actual-gemini-api-key"
```

Or add to `.env` file:
```
GEMINI_API_KEY=your-actual-gemini-api-key
```

### 3. Install Package (if not already done)

```bash
pip install requests
```

## Usage

### Python API

```python
from tajik_benchmark.council_evaluator import evaluate_answer, format_report

# Evaluate an answer
test_answer = "Салом! Ман хуб аст ва кори занат дорам."
test_question = "Чӣ хол доро ва чӣ кор мекунед?"

result = evaluate_answer(
    answer=test_answer,
    question=test_question,
    context="Casual conversational greeting"
)

# Print formatted report
print(format_report(result))
```

### Command Line Tool (Coming Soon)

```bash
tajik-bench evaluate-council \
  --answer "Салом! Ман хуб аст." \
  --question "Чӣ хол доро?" \
  --context "Casual greeting"
```

## Output Structure

The evaluator returns a comprehensive assessment with:

```json
{
  "individual_evaluations": {
    "strict_linguist": { /* scores and reasoning */ },
    "pragmatist": { /* scores and reasoning */ },
    "native_judge": { /* scores and reasoning */ }
  },
  "consensus": {
    "points_of_agreement": ["List of agreed-upon strengths"],
    "points_of_disagreement": { /* Where evaluators differ */ },
    "critical_issues": ["Deal-breaker problems if any"],
    "consensus_score_0_to_10": 8,
    "recommendation": "Final verdict"
  },
  "final_scores": {
    "grammaticality_score": { "average": 1.8, "min": 1, "max": 2 },
    "naturalness_score": { "average": 1.7, "min": 1, "max": 2 },
    "meaning_correctness_score": { "average": 2.0, "min": 2, "max": 2 },
    "instruction_adherence_score": { "average": 2.0, "min": 2, "max": 2 }
  },
  "overall_rating": "EXCELLENT (1.8-2.0)"
}
```

## Evaluation Ratings

- **EXCELLENT** (1.8-2.0): Response meets all criteria with minimal issues
- **GOOD** (1.5-1.8): Response is solid with minor imperfections
- **ACCEPTABLE** (1.0-1.5): Response completes the task but has notable issues
- **NEEDS IMPROVEMENT** (<1.0): Response has significant problems

## Batch Evaluation

To evaluate multiple answers:

```python
from tajik_benchmark.council_evaluator import evaluate_answer, format_report
import csv

# Load answers from CSV
results = []
with open("answers_to_evaluate.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        result = evaluate_answer(
            answer=row['answer'],
            question=row['question'],
            expected_answer=row.get('expected_answer'),
            context=row.get('context', '')
        )
        results.append({
            'question_id': row['id'],
            'consensus_score': result['consensus']['consensus_score_0_to_10'],
            'overall_rating': result['overall_rating'],
            'result': result
        })

# Save results
import json
with open("evaluation_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## Key Features

✅ **Three independent perspectives** - Avoids single-evaluator bias  
✅ **Rubric-aligned** - Uses official Tajik benchmark rubric  
✅ **Consensus generation** - Evaluators "discuss" to highlight agreement/disagreement  
✅ **Detailed reasoning** - Each persona explains their scores  
✅ **Batch processing** - Evaluate multiple answers efficiently  
✅ **Structured output** - JSON format for further analysis  

## Files

- `src/tajik_benchmark/council_evaluator.py` - Main module
- `COUNCIL_EVALUATOR_README.md` - This file
- `.env` - Store your API key here (not committed)

## Notes

- Responses are evaluated independently by each persona
- The consensus layer identifies where evaluators agree/disagree
- All evaluations include detailed reasoning
- Scores are averaged across the three evaluators
- Code-switching violations are counted separately

---

Created for the Tajik LLM Benchmark project. For questions, contact the research team.
