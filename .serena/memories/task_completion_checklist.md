# Task Completion Checklist

Before finishing a code task:
1. Prefer targeted Serena searches/symbol reads before editing.
2. Keep changes scoped to the requested behavior and existing module boundaries.
3. Preserve schema, dataset, collator, prompt, and checkpoint contracts unless the task explicitly changes them.
4. Add or update focused pytest coverage when behavior changes.
5. Run the most relevant tests; for broad changes, run `pytest`.
6. For training/inference paths, consider smoke commands only when dependencies, model checkpoint, and runtime cost make it practical.
7. Report any tests not run and why.

Common verification command:
```bash
pytest
```