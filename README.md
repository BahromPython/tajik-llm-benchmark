# Tajik LLM Benchmark

A reproducible framework for studying Tajik-language performance in large language models and whether pivot-language prompting changes accuracy, efficiency, or reliability.

## Research objective

The study compares direct Tajik prompting with Persian-, Russian-, and English-pivot conditions across grammar, factual knowledge, code-switching, and open-ended generation. It records answer quality together with token use, estimated API cost, latency, retries, failures, truncation, and format compliance.

The mentor-approved benchmark contains 1,600 items balanced across four task categories and formal and conversational registers.

| Partition | Items | Purpose |
|---|---:|---|
| Development | 200 | Prompt, rubric, and pipeline development |
| Primary test | 800 | Confirmatory model comparison |
| Robustness | 400 | Sensitivity analysis |
| Reserve | 200 | Replacement under documented rules |

Raw benchmark items, answer keys, approval evidence, credentials, and generated responses are excluded from Git to protect the held-out evaluation.

## Experimental design

- Three version-locked models from each of OpenAI, Anthropic, and Google.
- Four matched conditions per item: direct Tajik, Persian pivot, Russian pivot, and English pivot.
- Stateless requests with fixed decoding parameters and recorded model identifiers.
- Append-only, resumable collection with deterministic request IDs.
- Exact scoring for closed-form tasks and blinded human evaluation for generation.
- Paired analyses, confidence intervals, multiple-comparison correction, and inter-rater reliability.
- Efficiency measures including tokens, latency, cost, failures, and cost per correct response.

No empirical model results are reported until collection and human evaluation are complete.

## Repository structure

```text
configs/              experiment and scoring configurations
data/                 local-only benchmark data and access notes
docs/                 methodology and reproducibility documentation
professor_dashboard/  aggregate-results dashboard
runs/                 local-only experimental artifacts
src/tajik_benchmark/  benchmark package
tests/                automated tests
```

## Setup

Python 3.11 or newer is required. The package uses only the standard library at runtime.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --editable .
```

Store credentials only in environment variables. Never commit a populated `.env` file.

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:ANTHROPIC_API_KEY = "your-key"
$env:GEMINI_API_KEY = "your-key"
```

## Reproducible workflow

```powershell
tajik-bench validate --items data/dataset1_professor_validated_1600_v1.csv
python -m unittest discover -s tests -v
tajik-bench plan --items data/dataset1_professor_validated_1600_v1.csv --config configs/api_smoke_test_3_v1.json --output runs/api-smoke-plan.jsonl
tajik-bench run --plan runs/api-smoke-plan.jsonl --output runs/api-smoke-raw.jsonl --pricing configs/api_pricing_2026-09-09.json --max-cost-usd 0.25
```

The runner writes every response immediately, resumes completed requests, retries transient failures, and records provider usage fields and the dated pricing snapshot. Full procedures are in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Research integrity

Only development items may guide prompt, rubric, or model-selection decisions. Primary-test and robustness items must not be inspected, edited, or used for model selection after the experiment is frozen. Reserve substitutions must follow a documented, model-blind rule.

## Current status

- Dataset structure and all 1,600 items approved by the research mentor.
- Validation, planning, provider adapters, response logging, scoring, analysis, and dashboard generation implemented.
- Live response collection and human rating pending.

## Author

Bahrom Ashurov — Lumiere research project.

## License and citation

Code and data reuse terms are not yet finalized. See [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff). Contact the author before redistributing benchmark items or answer keys.
