# Style And Conventions

Observed conventions:
- Python source uses modern type hints (`list[str]`, `str | Path`, typed return values).
- Data containers use `@dataclass(slots=True)` where appropriate.
- Data contracts use Pydantic `BaseModel`.
- Module and function names are snake_case; classes are PascalCase.
- Entry-point scripts use `argparse` and expose a `main() -> None` guarded by `if __name__ == "__main__"` where applicable.
- Package uses `src` layout with imports under `chargellm`.
- Tests are simple pytest functions named `test_*`.
- JSON outputs and prompt completions are treated as structured contract surfaces.

Engineering patterns:
- Keep dataset/schema/collator contracts stable; tests cover these heavily.
- SFT and GRPO both use local JSON datasets converted into Hugging Face-compatible records.
- Training/checkpoint code splits LLM adapter state from TS-side wrapper state, because time-series modules are not part of the base Hugging Face causal LM.
- Reward functions are intentionally narrow and programmatic: JSON parse validity, label correctness, field completeness/confidence range, key-process validity, and brevity constraints.

No formatter/linter configuration was found in `pyproject.toml` beyond pytest settings. Follow existing style and run `pytest` after changes.