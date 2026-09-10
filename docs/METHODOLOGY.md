# Methodology and reproducibility protocol

## Design

This is a within-item, paired benchmark study. Every eligible item is submitted under direct Tajik, Persian-pivot, Russian-pivot, and English-pivot conditions. Model and condition order should be randomized from a recorded seed. Requests are independent and stateless.

The frozen bank contains 1,600 mentor-approved items divided into development (200), primary test (800), robustness (400), and reserve (200). It is balanced across grammar, factual knowledge, code-switching, and generation, and across formal and conversational registers.

## Model comparison

The planned comparison includes three version-locked models from each of OpenAI, Anthropic, and Google. Exact model identifiers, access dates, decoding settings, prompt-template hashes, dataset checksum, random seed, and pricing-snapshot date must be recorded before the held-out run. A model substitution after collection begins constitutes a separate run.

## Outcomes

The primary outcome is accuracy on objectively scored held-out items. Secondary quality outcomes include category- and register-specific accuracy, code-switch compliance, format compliance, and blinded rubric scores for generation. Efficiency outcomes include input, output, and total tokens; latency; retries; failures; truncation; estimated API cost; tokens per correct answer; and cost per correct answer.

Provider-reported token counts remain separate from local estimates. Missing usage data remain missing rather than being converted to zero. Cost is calculated from the dated pricing configuration and reported as an estimate.

## Human evaluation

Open-ended responses require human review. Responses should be anonymized, randomized, and presented without provider, model, or condition labels. At least two Tajik-proficient raters should independently score a prespecified overlap subset. Disagreements are adjudicated under a written rubric, and weighted kappa is reported for ordinal ratings.

Raters assess task fulfillment, grammaticality, fluency, register appropriateness, factuality when applicable, unnecessary foreign-language insertion, and safety or refusal behavior. The report must state responses per rater, overlap size, missing judgments, adjudications, and reliability.

## Collection procedure

1. Validate schema, IDs, split counts, and answer fields.
2. Freeze the dataset checksum, prompts, models, settings, seed, and pricing snapshot.
3. Run one request per provider and inspect response, model, usage, and cost fields.
4. Run the development pilot and resolve only prespecified technical problems.
5. Freeze the protocol before unlocking held-out planning.
6. Collect with append-only output, automatic resume, bounded retries, and explicit failure records.
7. Preserve raw responses unchanged; create scored and analyzed derivatives as new files.
8. Conduct blinded evaluation and calculate reliability before revealing model labels.
9. Generate aggregate tables and a dashboard without exposing prompts or answer keys.

## Statistical analysis

Analyses are paired because conditions share items. Report point estimates and 95% confidence intervals. Binary paired comparisons use exact McNemar tests; score differences use paired bootstrap intervals. Apply Holm correction within each declared family of comparisons. Category and register breakdowns are secondary, and confirmatory results must be distinguished from exploratory analyses.

Missing or failed responses count as failures in the primary intention-to-test analysis. A sensitivity analysis may report accuracy among successful requests, clearly labeled. Robustness conclusions use the separate robustness partition.

## Contamination controls

Only development items may guide prompt, rubric, or model decisions. Held-out prompts and answers must not be committed or pasted into unrelated provider conversations. Reserve substitutions must be selected without reference to performance and documented with the original item ID and reason.

## Reporting

The final report should include dataset composition, exclusions, exact model versions, access dates, prompts, inference settings, request counts, missingness, token and cost accounting, quality outcomes, uncertainty intervals, corrected tests, inter-rater reliability, limitations, and a data-availability statement.
