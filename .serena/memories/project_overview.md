# Project Overview

ChargeLLM is a Python TS-LLM project for battery diagnosis from multiple charging-history time series. It combines time-series encoding, battery-level history aggregation, a bridge into an LLM hidden space, Qwen Instruct + LoRA generation, structured JSON diagnosis output, SFT, and GRPO.

Primary output is a structured diagnosis object with fields such as `label`, `confidence`, `key_processes`, and explanation. Labels include `电池故障`, `电池老化`, `非标电池`, and `正常`.

Tech stack:
- Python >= 3.11
- PyTorch, Transformers, PEFT, TRL, Accelerate
- Hugging Face `datasets`
- Pydantic v2 schemas
- pytest / pytest-cov for tests
- setuptools with `src` package layout

Important data files:
- `dataset/sft.json`
- `dataset/grpo.json`
- `dataset/origin.jsonl`
- `dataset/synthetic_sft.json`
- `dataset/synthetic_grpo.json`
- `dataset/synthetic_origin.jsonl`

Docs:
- `docs/architecture.md`
- `docs/data_contract.md`
- `docs/sft_grpo_plan.md`
- `docs/testing_strategy.md`