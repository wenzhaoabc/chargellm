from __future__ import annotations

from peft import LoraConfig
from peft import TaskType


DEFAULT_LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]

DEFAULT_LLM_MODULES_TO_SAVE: list[str] = []

WRAPPER_MODULES_TO_SAVE = [
    "process_encoder",
    "history_aggregator",
    "bridge",
    "label_head",
    "confidence_head",
]


def build_qwen_lora_config(
    r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    target_modules: list[str] | None = None,
    modules_to_save: list[str] | None = None,
) -> LoraConfig:
    resolved_modules_to_save = modules_to_save if modules_to_save is not None else DEFAULT_LLM_MODULES_TO_SAVE
    return LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules or DEFAULT_LORA_TARGET_MODULES,
        modules_to_save=resolved_modules_to_save or None,
        bias="none",
    )