from chargellm.data.hf_builders import build_grpo_hf_dataset
from chargellm.data.hf_builders import build_sft_hf_dataset


def test_build_sft_hf_dataset() -> None:
    dataset = build_sft_hf_dataset("dataset/sft.json")
    row = dataset[0]
    assert "prompt" in row
    assert "completion" in row
    assert row["label"] == "电池故障"


def test_build_grpo_hf_dataset() -> None:
    dataset = build_grpo_hf_dataset("dataset/grpo.json")
    row = dataset[0]
    assert "prompt" in row
    assert "label" in row
    assert "process_ids" in row