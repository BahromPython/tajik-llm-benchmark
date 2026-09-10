# Benchmark data

The approved 1,600-item benchmark and its answer keys are intentionally not tracked in Git. This prevents test-set contamination and protects unpublished research material.

Authorized researchers should place the validated file here as `dataset1_professor_validated_1600_v1.csv`.

Expected composition:

- 1,600 unique items
- 200 development, 800 primary-test, 400 robustness, and 200 reserve items
- 400 items in each of grammar, factual knowledge, code-switching, and generation
- 800 formal and 800 conversational items

Run `tajik-bench validate --items data/dataset1_professor_validated_1600_v1.csv` before creating an experiment plan. Do not publish prompts, answer keys, or item-level model outputs before the release policy is finalized.
