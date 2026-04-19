# Codebase Structure

Root layout:
- `src/chargellm/`: main package
- `tests/`: pytest suite
- `scripts/`: utility scripts such as synthetic data generation
- `docs/`: architecture, data contract, training plan, testing strategy
- `dataset/`: local sample and synthetic datasets
- `pyproject.toml`: package metadata and pytest config
- `requirements.txt`: runtime and dev dependencies

Main package modules:
- `src/chargellm/data/`: dataset loading, collators, HF dataset builders
  - `BatteryJsonDataset`
  - `BatteryCollator`, `BatteryBatch`
  - `TSQwenSFTCollator`, `TSQwenGRPOCollator`, `TSQwenBatch`
  - `build_sft_hf_dataset`, `build_grpo_hf_dataset`
- `src/chargellm/schemas/`: Pydantic data/output contracts
  - `ChargingProcessRecord`, `BatterySample`, `CanonicalBatterySample`
  - `DiagnosisOutput`
- `src/chargellm/llm/`: prompt construction and LoRA config
  - `build_process_summary`, `build_user_prompt`, `build_sft_completion`, `build_sft_prompt_record`, `build_grpo_prompt_record`
  - `build_qwen_lora_config`
- `src/chargellm/training/`: SFT, GRPO, checkpoint helpers
  - `train_sft`, `train_grpo`
  - `save_wrapper_checkpoint`, `load_tsqwen_checkpoint`, `infer_wrapper_dimensions`
- `src/chargellm/rewards/`: programmatic GRPO rewards
  - JSON validity, label correctness, confidence range, key-process validity
- `src/chargellm/inference/`: demo inference entry point

Testing focuses on schema parsing, dataset loading, collator shapes/masks, model forward smoke behavior, prompt formatting, rewards, checkpointing, and inference schema validity.