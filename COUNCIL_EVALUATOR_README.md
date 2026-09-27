# Tajik LLM Council Evaluator

A three-personality evaluation system that independently assesses Tajik language responses. **Exports results in the official `tajik-human-review-v1` schema** (matching the review interface).

## System Overview

Three independent evaluators assess each answer using the **official 5-dimension rubric**:

1. **Dr. Linguist** - Rigorous grammarian focused on linguistic precision
2. **Pragmatist** - Task-completion focused evaluator
3. **Native Speaker** - Authenticity and fluency expert

### Evaluation Dimensions

Each evaluator independently scores on **5 dimensions** (0-2 scale):

| Dimension | Definition |
|-----------|-----------|
| **Grammaticality** | Correct Tajik grammar and syntax |
| **Naturalness** | Natural, idiomatic Tajik phrasing |
| **Meaning Correctness** | Core answer is correct and factually accurate |
| **Instruction Adherence** | Task completed in correct format |
| **Register Fit** | Formal/informal register appropriateness |

**Plus:** Unwanted code-switching detection (yes/no/unclear)

## Export Schema

Results are exported in the **tajik-human-review-v1 schema** (matches the HTML review interface):

```json
{
  "export_schema": "tajik-human-review-v1",
  "study_id": "council-eval",
  "assigned_count": 1,
  "completed_count": 1,
  "ratings": [
    {
      "study_id": "council-eval",
      "reviewer_id": "dr-linguist",
      "reviewer_name": "Dr. Linguist",
      "blind_id": "response-001",
      "item_id": "item-001",
      "grammaticality": 2,
      "naturalness": 2,
      "meaning_correctness": 2,
      "instruction_adherence": 2,
      "register_fit": 2,
      "unwanted_code_switching": "no",
      "notes": "Detailed assessment from this evaluator",
      "flagged": false,
      "complete": true,
      "updated_at_utc": "2026-09-27T15:30:00Z"
    },
    { /* ... Pragmatist evaluation ... */ },
    { /* ... Native Speaker evaluation ... */ }
  ]
}
```

**One record per evaluator** → Three evaluations per item

## Setup

### 1. Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Create a free API key
3. Copy it

### 2. Set Environment Variable

```bash
export GEMINI_API_KEY="your-actual-gemini-api-key"
```

Or add to `.env`:
```
GEMINI_API_KEY=your-actual-gemini-api-key
```

### 3. Install Dependencies

```bash
pip install requests
```

## Usage

### Evaluate Single Answer (exports JSON/CSV/HTML)

```bash
python -m tajik_benchmark.cli_council eval \
  --answer "Салом! Ман хуб аст." \
  --question "Чӣ хол доро?" \
  --blind-id "response-001" \
  --item-id "item-001" \
  --output results/eval-001
```

**Outputs:**
- `eval-001.json` - Export schema JSON (3 evaluations)
- `eval-001.csv` - Export schema CSV (3 rows)
- `eval-001_report.html` - HTML report showing all evaluations

### Evaluate Batch from CSV

```bash
python -m tajik_benchmark.cli_council batch \
  --input answers.csv \
  --output batch_results \
  --study-id "tajik-benchmark-2026"
```

**Input CSV format:**
```csv
answer,question,item_id,blind_id,expected_answer,context
"Салом!","Чӣ хол доро?","item-001","blind-001","Expected...","Context..."
```

**Outputs:**
- `batch_results.json` - All evaluations in export schema
- `batch_results.csv` - All evaluations as CSV rows

### Python API

```python
from tajik_benchmark.council_evaluator import (
    evaluate_answer,
    export_to_json,
    export_to_csv,
    generate_html_report,
)

result = evaluate_answer(
    answer="Салом! Ман хуб аст.",
    question="Чӣ хол доро?",
    item_id="item-001",
    blind_id="blind-001"
)

# Export in all formats
export_to_json(result, "result.json")
export_to_csv(result, "result.csv")

html = generate_html_report(result)
with open("report.html", "w") as f:
    f.write(html)
```

## Output Files

### JSON Export (tajik-human-review-v1)

```json
{
  "export_schema": "tajik-human-review-v1",
  "ratings": [
    { "reviewer_id": "dr-linguist", "grammaticality": 2, ... },
    { "reviewer_id": "pragmatist", "grammaticality": 2, ... },
    { "reviewer_id": "native-speaker", "grammaticality": 2, ... }
  ]
}
```

### CSV Export (tajik-human-review-v1)

Columns: study_id, reviewer_id, reviewer_name, blind_id, item_id, grammaticality, naturalness, meaning_correctness, instruction_adherence, register_fit, unwanted_code_switching, notes, flagged, complete, updated_at_utc

### HTML Report

Visual report showing:
- Question and response
- All three evaluators' scores (side-by-side)
- Code-switching assessment
- Reviewer notes
- Consensus scores (average across evaluators)

## Key Features

✅ **Three independent evaluators** - Avoids single-evaluator bias  
✅ **Official schema** - Exports match the HTML review interface format  
✅ **5-dimension rubric** - Grammaticality, naturalness, meaning, adherence, register  
✅ **Code-switching detection** - Flags unjustified Russian/English  
✅ **Multiple formats** - JSON, CSV, and HTML reports  
✅ **Batch processing** - Evaluate 100+ answers efficiently  
✅ **Consensus scores** - Average ratings across evaluators  

## File Structure

```
src/tajik_benchmark/
├── council_evaluator.py      # Main evaluation engine
├── cli_council.py            # Command-line interface
└── COUNCIL_EVALUATOR_README.md  # This file

.env                           # API key (not committed)
```

## Integration with Review Interface

The export schema is **compatible with** the official review HTML interface:
- Same dimension names
- Same scoring scale (0-2)
- Same metadata structure
- Same CSV/JSON format

You can:
- Export evaluations and import into the review interface
- Combine with human evaluations
- Use in analysis pipelines
- Create aggregate reports

## Example Workflow

```bash
# Evaluate a set of responses
python -m tajik_benchmark.cli_council batch \
  --input responses.csv \
  --study-id "pilot-2026"

# Result: pilot-2026.json, pilot-2026.csv, pilot-2026_report.html

# The CSV/JSON can be imported into the review interface for:
# - Comparison with human ratings
# - Consensus analysis
# - Quality control
```

## Notes

- Each answer generates **3 evaluations** (one per evaluator)
- Evaluators work **independently** with no cross-contamination
- Scores range from **0-2** (does not meet / partly meets / meets)
- `complete` field is true only when all dimensions and code-switching are scored
- `flagged` field can be used to mark evaluations needing review

---

Created for the Tajik LLM Benchmark. For questions, see the research documentation.
