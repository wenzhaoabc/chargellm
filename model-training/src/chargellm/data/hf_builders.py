from __future__ import annotations

from datasets import Dataset

from chargellm.data.dataset import BatteryJsonDataset
from chargellm.llm.prompting import build_grpo_prompt_record
from chargellm.llm.prompting import build_sft_prompt_record


def build_sft_hf_dataset(file_path: str) -> Dataset:
    dataset = BatteryJsonDataset(file_path)
    return Dataset.from_list([build_sft_prompt_record(sample) for sample in dataset])


def build_grpo_hf_dataset(file_path: str) -> Dataset:
    dataset = BatteryJsonDataset(file_path)
    return Dataset.from_list([build_grpo_prompt_record(sample) for sample in dataset])