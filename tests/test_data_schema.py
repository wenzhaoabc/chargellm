import json
from pathlib import Path

from chargellm.schemas.data_schema import BatterySample


def test_sft_sample_parses() -> None:
    file_path = Path("dataset/sft.json")
    sample = json.loads(file_path.read_text(encoding="utf-8"))[0]
    parsed = BatterySample.model_validate(sample)
    assert parsed.reason is not None


def test_grpo_sample_parses() -> None:
    file_path = Path("dataset/grpo.json")
    sample = json.loads(file_path.read_text(encoding="utf-8"))[0]
    parsed = BatterySample.model_validate(sample)
    assert parsed.reason is None


def test_synthetic_sft_sample_parses() -> None:
    file_path = Path("dataset/synthetic_sft.json")
    sample = json.loads(file_path.read_text(encoding="utf-8"))[0]
    parsed = BatterySample.model_validate(sample)
    assert parsed.reason is not None
    assert 120 <= len(parsed.charging_process[0].current_series) <= 360


def test_synthetic_grpo_sample_parses() -> None:
    file_path = Path("dataset/synthetic_grpo.json")
    sample = json.loads(file_path.read_text(encoding="utf-8"))[0]
    parsed = BatterySample.model_validate(sample)
    assert parsed.reason is None
    assert 120 <= len(parsed.charging_process[0].current_series) <= 360
