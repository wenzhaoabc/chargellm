import torch

from chargellm.data.ts_qwen_collator import TSQwenGRPOCollator
from chargellm.data.ts_qwen_collator import TSQwenSFTCollator
from chargellm.schemas.data_schema import BatterySample


class FakeTokenizer:
    pad_token_id = 0
    eos_token_id = 1

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        text = "".join(f"<{item['role']}>{item['content']}" for item in messages)
        if add_generation_prompt:
            text += "<assistant>"
        return text

    def __call__(self, text, add_special_tokens=False, truncation=False, max_length=None, padding=False, return_tensors=None):
        texts = text if isinstance(text, list) else [text]
        encoded_sequences = []
        for item in texts:
            tokens = [((ord(char) % 50) + 2) for char in item]
            if max_length is not None:
                tokens = tokens[:max_length]
            encoded_sequences.append({"input_ids": tokens, "attention_mask": [1] * len(tokens)})

        if not padding and return_tensors is None and len(encoded_sequences) == 1:
            return encoded_sequences[0]

        max_len = max(len(item["input_ids"]) for item in encoded_sequences)
        padded_ids = []
        padded_mask = []
        for item in encoded_sequences:
            pad_len = max_len - len(item["input_ids"])
            padded_ids.append(item["input_ids"] + [self.pad_token_id] * pad_len)
            padded_mask.append(item["attention_mask"] + [0] * pad_len)

        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor(padded_ids, dtype=torch.long),
                "attention_mask": torch.tensor(padded_mask, dtype=torch.long),
            }

        if len(texts) == 1:
            return {"input_ids": padded_ids[0], "attention_mask": padded_mask[0]}
        return {
            "input_ids": padded_ids,
            "attention_mask": padded_mask,
        }


def _sample() -> BatterySample:
    return BatterySample.model_validate(
        {
            "battery_id": "battery-001",
            "label": "正常",
            "reason": "状态稳定。",
            "charging_process": [
                {
                    "process_id": "p1",
                    "current_series": [1.0, 2.0],
                    "voltage_series": [3.0, 4.0],
                    "power_series": [5.0, 6.0],
                    "charge_capacity": [7.0, 8.0],
                }
            ],
        }
    )


def test_tsqwen_sft_collator_masks_prompt_tokens() -> None:
    collator = TSQwenSFTCollator(FakeTokenizer(), max_length=256)
    batch = collator([_sample()])
    assert batch.lm_labels is not None
    assert torch.any(batch.lm_labels == -100)
    assert tuple(batch.input_ids.shape) == tuple(batch.lm_labels.shape)


def test_tsqwen_grpo_collator_builds_prompt_only_batch() -> None:
    collator = TSQwenGRPOCollator(FakeTokenizer(), max_length=256)
    batch = collator([_sample()])
    assert batch.lm_labels is None
    assert batch.prompt_texts
    assert tuple(batch.input_ids.shape) == tuple(batch.attention_mask.shape)