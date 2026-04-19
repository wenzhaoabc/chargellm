import json

from chargellm.llm.prompting import build_grpo_prompt_record
from chargellm.llm.prompting import build_sft_prompt_record
from chargellm.schemas.data_schema import BatterySample


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


def test_build_sft_prompt_record() -> None:
    record = build_sft_prompt_record(_sample())
    assert len(record["prompt"]) == 2
    payload = json.loads(record["completion"][0]["content"])
    assert payload["label"] == "正常"


def test_build_grpo_prompt_record() -> None:
    record = build_grpo_prompt_record(_sample())
    assert record["label"] == "正常"
    assert record["process_ids"] == ["p1"]