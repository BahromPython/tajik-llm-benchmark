# Benchmark implementation status

## Implemented and verified

- Current split names are supported: development, primary_test, robustness, and reserve.
- Primary, robustness, and reserve splits remain code-locked by default.
- Held-out planning rejects placeholder model identifiers.
- Plans are deterministically randomized with a recorded seed.
- The pilot supports stratified sampling across category and register.
- A matched-length Tajik control and three translation-only controls are available.
- Raw records support input, output, cached, reasoning, and total tokens; token source; latency; retries; request status; and provider metadata.
- Scored records include response words, characters, empty-response flags, and format violations.
- Analysis summarizes accuracy and operational efficiency by model and condition.
- Full-stimulus auditing checks prompt plus grammar choices, avoiding false duplicate warnings.
- A 96-item stratified professor-review sheet has been generated.
- Twelve automated tests pass.
- The 80-item, five-condition mock pilot completed 400 planned requests end to end.

## Current dataset audit

- 1,600 items and 1,600 unique IDs.
- 400 items in each task category.
- 800 formal and 800 conversational items.
- 200 development, 800 primary-test, 400 robustness, and 200 reserve items.
- No exact complete-stimulus duplicates.
- No near-duplicate pairs at five-word-shingle Jaccard threshold 0.82.
- No missing prompt, source, or subtype fields.
- All 1,600 rows are currently marked professor_validated=false.

## Decisions requiring confirmation

1. Exact model identifiers and access modes.
2. Collection start and end dates.
3. Whether the matched-length Tajik control belongs in the main experiment or development-only diagnostics.
4. The precise definition of each robustness target and how robustness items map to originals.
5. The accepted-loanword list for code-switch scoring.
6. Which second Tajik rater will independently score at least 25 percent of open-ended outputs.
7. Whether the professor will review the 96-item stratified sample or a larger sample.
8. API budget and maximum acceptable number of real requests.

## Work requiring external access or humans

- Real ChatGPT, Claude, Gemini, and optional Qwen collection requires exact models and credentials or a documented manual protocol.
- Item-level Tajik correctness and naturalness require qualified human review.
- Public-release licensing requires source-by-source verification.
- Energy or carbon estimates require credible provider or hardware measurements and are intentionally omitted for now.
