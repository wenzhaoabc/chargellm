from __future__ import annotations

from dataclasses import dataclass

import torch

from chargellm.data.collator import BatteryBatch
from chargellm.data.collator import BatteryCollator
from chargellm.llm.prompting import build_grpo_prompt_record
from chargellm.llm.prompting import build_sft_prompt_record
from chargellm.schemas.data_schema import BatterySample
from chargellm.schemas.data_schema import LABEL_TO_ID


@dataclass(slots=True)
class TSQwenBatch:
    timeseries: BatteryBatch
    input_ids: torch.Tensor
    attention_mask: torch.Tensor
    lm_labels: torch.Tensor | None
    class_labels: torch.Tensor
    prompt_texts: list[str]
    completion_texts: list[str]

class TSQwenSFTCollator:
    def __init__(self, tokenizer, max_length: int = 1024):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.timeseries_collator = BatteryCollator()

    def __call__(self, samples: list[BatterySample]) -> TSQwenBatch:
        timeseries_batch = self.timeseries_collator(samples)
        prompt_texts: list[str] = []
        completion_texts: list[str] = []
        full_texts: list[str] = []

        for sample in samples:
            record = build_sft_prompt_record(sample)
            prompt_text = self.tokenizer.apply_chat_template(
                record["prompt"],
                tokenize=False,
                add_generation_prompt=True,
            )
            full_text = self.tokenizer.apply_chat_template(
                record["prompt"] + record["completion"],
                tokenize=False,
                add_generation_prompt=False,
            )
            prompt_texts.append(prompt_text)
            full_texts.append(full_text)
            completion_texts.append(record["completion"][0]["content"])

        encoded_prompts = self.tokenizer(
            prompt_texts,
            add_special_tokens=False,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )
        padded = self.tokenizer(
            full_texts,
            add_special_tokens=False,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )
        lm_labels_tensor = padded["input_ids"].clone()
        prompt_lengths = encoded_prompts["attention_mask"].sum(dim=1)
        for row_index, prompt_len in enumerate(prompt_lengths.tolist()):
            lm_labels_tensor[row_index, :prompt_len] = -100
        lm_labels_tensor[padded["attention_mask"] == 0] = -100
        return TSQwenBatch(
            timeseries=timeseries_batch,
            input_ids=padded["input_ids"],
            attention_mask=padded["attention_mask"],
            lm_labels=lm_labels_tensor,
            class_labels=timeseries_batch.labels,
            prompt_texts=prompt_texts,
            completion_texts=completion_texts,
        )


class TSQwenGRPOCollator:
    def __init__(self, tokenizer, max_length: int = 1024):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.timeseries_collator = BatteryCollator()

    def __call__(self, samples: list[BatterySample]) -> TSQwenBatch:
        timeseries_batch = self.timeseries_collator(samples)
        prompt_texts: list[str] = []

        for sample in samples:
            record = build_grpo_prompt_record(sample)
            prompt_text = self.tokenizer.apply_chat_template(
                record["prompt"],
                tokenize=False,
                add_generation_prompt=True,
            )
            prompt_texts.append(prompt_text)

        padded = self.tokenizer(
            prompt_texts,
            add_special_tokens=False,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )
        return TSQwenBatch(
            timeseries=timeseries_batch,
            input_ids=padded["input_ids"],
            attention_mask=padded["attention_mask"],
            lm_labels=None,
            class_labels=torch.tensor([LABEL_TO_ID[sample.label] for sample in samples], dtype=torch.long),
            prompt_texts=prompt_texts,
            completion_texts=[],
        )