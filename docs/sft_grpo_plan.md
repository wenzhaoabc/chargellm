# SFT and GRPO Plan

## SFT

### Source

- `dataset/sft.json`

### Input

- battery charging history tensors
- prompt instruction asking for structured JSON diagnosis

### Supervision Target

The model learns to generate:

- `label`
- `confidence`
- `key_processes`
- `explanation`

`explanation` is supervised from the dataset `reason` field.

### Data Shape

SFT samples are converted into prompt-completion format compatible with `SFTTrainer`.

Current repository support:

- `build_sft_hf_dataset()` creates Hugging Face datasets from `dataset/sft.json`
- prompt records use system and user messages
- completion records are strict JSON strings
- `TSQwenSFTCollator` builds prompt-conditioned LM labels with prompt masking
- `train_sft()` runs a real custom loop with AMP, gradient clipping, and checkpoint saving

## GRPO

### Source

- `dataset/grpo.json`

### Input

- battery charging history tensors
- diagnosis instruction prompt

### Reward Functions

The first milestone uses only programmatic rewards:

1. label correctness reward
2. JSON validity reward
3. field completeness reward
4. confidence range reward
5. key process validity reward
6. brevity penalty for excessively long explanations

### Deliberate Constraint

The first GRPO version does not score mechanism fidelity or expert-level chemistry statements.

It only rewards what is directly verifiable from current data.

Current repository support:

- `build_grpo_hf_dataset()` creates prompt-only datasets from `dataset/grpo.json`
- reward functions operate on generated JSON text plus label and process metadata
- `train_grpo()` restores a TS-Qwen checkpoint and runs a grouped relative policy loop
- inference reuses the same checkpoint restore path as training continuation