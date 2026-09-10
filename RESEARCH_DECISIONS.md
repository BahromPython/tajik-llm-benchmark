# Research decisions and run ledger

This file is the durable record of decisions made for the Tajik LLM benchmark. Update it before every frozen run.

## Confirmed

- Researcher: Bahrom Ashurov.
- Topic: benchmarking LLM performance in Tajik, with task-dependent effects of Persian, Russian, and English pivot prompting.
- Dataset: 1,600 items; 200 development, 800 primary test, 400 robustness, 200 reserve.
- Balance: 400 items per category; 800 formal and 800 conversational.
- Categories: grammar, factual knowledge, code-switching, and generation.
- Professor approval: Davlat Karaboev confirmed by email that the dataset looks great and has a good structure; the researcher confirmed that the approval covered the full dataset.
- Validated frozen file: `data/dataset1_professor_validated_1600_v1.csv`.
- Pilot models: three cost/capability tiers from OpenAI, Anthropic, and Google, excluding GPT-6 Astra and Claude Fable because of cost.
- Primary pilot conditions: direct Tajik, Persian pivot, Russian pivot, English pivot.
- Confound control: an 80-item matched-length Tajik diagnostic across all nine models (720 requests) tests whether extra instruction alone explains pivot gains.
- Translation control: after model selection, an 80-item translation-only diagnostic across three pivots and three winning models (720 requests) measures meaning loss separately from task solving.
- Collection mode: stateless, one request per item-condition-model, tools disabled, one repetition initially.
- Resource measures: provider-reported input/output/cached/reasoning/total tokens where available, dated estimated cost, latency, retries, failures, empty responses, output length, and format violations.
- Results dashboard: aggregate data only; held-out prompts, gold answers, and raw responses are excluded.

## Not yet confirmed — do not start the full held-out run

- Availability of paid OpenAI and Anthropic API accounts (Plus subscriptions do not include API credits).
- Maximum total API budget in USD.
- Whether 200 development items are affordable after the one-request smoke test.
- Pre-registered rule for selecting final models after the nine-model pilot.
- Whether the final test uses 800 items with one model per provider, or a smaller balanced sample with all nine.
- Human-rating plan for open generation and code-switching outputs, including a second Tajik-speaking rater.
- Public-release decision for aggregate results and dataset licensing.
- Final pricing verification and experiment timestamps.

## Proposed model-selection rule

Select one model per provider using development data only. Rank models by objective accuracy, then use estimated
cost per correct response as the tie-breaker. Do not inspect primary-test responses until this rule and the selected
models are recorded here.

## Run ledger

| Run | Split | Models | Conditions | Requests | Budget ceiling | Status |
|---|---|---:|---:|---:|---:|---|
| nine-model-pilot-v1 | development | 9 | 4 | 7,200 | part of $25 total | prepared, not started |
| matched-control-v1 | development | 9 | 1 | 720 | part of $25 total | prepared, not started |
