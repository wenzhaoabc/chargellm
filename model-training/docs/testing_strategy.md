# Testing Strategy

## Priority

Tests are written for contract stability and pipeline smoke coverage.

## First-Wave Tests

1. schema parsing for SFT and GRPO samples
2. dataset loading from local JSON files
3. collator padding and mask shapes
4. joint model forward pass output shapes
5. SFT formatting contract
6. GRPO reward function behavior
7. Hugging Face SFT and GRPO dataset builder output shape
8. prefix embedding preparation for TS-Qwen inputs
9. tokenizer-aware TS-Qwen collator label masking behavior
10. checkpoint save and restore behavior
11. GRPO helper functions for rewards and label masking

## Non-Goals

- no large integration benchmarks yet
- no GPU-dependent training tests in CI scope
- no generated text quality benchmark in the first wave

## Smoke Criteria

A first milestone is considered valid when:

1. local datasets parse successfully
2. one batch collates successfully
3. the model forward pass runs on CPU
4. reward functions score a mock completion correctly
5. inference produces a schema-valid output object