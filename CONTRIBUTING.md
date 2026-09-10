# Contributing

This repository supports an active research study. Changes must preserve reproducibility and the separation between development and held-out data.

1. Do not add credentials, benchmark CSV files, answer keys, approval correspondence, or generated responses.
2. Do not change frozen prompts, scoring rules, models, or held-out data without a new protocol version.
3. Add or update tests for behavioral changes.
4. Run `python -m unittest discover -s tests -v`.
5. Explain any effect on comparability with earlier runs.

Bug reports should include the command, Python version, configuration filename, and sanitized error output.
