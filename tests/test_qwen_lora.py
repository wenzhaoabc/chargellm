from chargellm.llm.qwen_lora import DEFAULT_LLM_MODULES_TO_SAVE
from chargellm.llm.qwen_lora import DEFAULT_LORA_TARGET_MODULES
from chargellm.llm.qwen_lora import WRAPPER_MODULES_TO_SAVE
from chargellm.llm.qwen_lora import build_qwen_lora_config


def test_build_qwen_lora_config() -> None:
    config = build_qwen_lora_config()
    assert set(config.target_modules) == set(DEFAULT_LORA_TARGET_MODULES)
    assert config.modules_to_save is None
    assert "bridge" in WRAPPER_MODULES_TO_SAVE
