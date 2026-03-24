from __future__ import annotations

import json

from chargellm.schemas.data_schema import BatterySample


DEFAULT_SYSTEM_PROMPT = (
    "你是一个电池充电历史诊断模型。"
    "你必须结合时序编码特征与用户给出的充电历史摘要，"
    "输出严格合法的 JSON，字段仅包含 label、confidence、key_processes、explanation。"
    "不要输出额外字段，不要输出 markdown。"
)


def build_process_summary(sample: BatterySample, max_processes: int = 8) -> str:
    summaries: list[str] = []
    for process in sample.charging_process[:max_processes]:
        summaries.append(
            " | ".join(
                [
                    f"process_id={process.process_id}",
                    f"points={len(process.current_series)}",
                    f"current_end={process.current_series[-1]:.4f}",
                    f"voltage_end={process.voltage_series[-1]:.4f}",
                    f"power_end={process.power_series[-1]:.4f}",
                    f"capacity_end={process.charge_capacity[-1]:.4f}",
                ]
            )
        )
    return "\n".join(summaries)


def build_user_prompt(sample: BatterySample) -> str:
    return (
        f"battery_id={sample.battery_id}\n"
        f"process_count={len(sample.charging_process)}\n"
        "最近充电过程摘要如下：\n"
        f"{build_process_summary(sample)}\n"
        "请结合时序前缀信息输出 JSON 诊断结果。"
    )


def build_sft_completion(sample: BatterySample) -> str:
    return json.dumps(
        {
            "label": sample.label,
            "confidence": 0.8,
            "key_processes": [
                process.process_id for process in sample.charging_process[: min(2, len(sample.charging_process))]
            ],
            "explanation": sample.reason or "未提供解释。",
        },
        ensure_ascii=False,
    )


def build_sft_prompt_record(sample: BatterySample) -> dict[str, object]:
    return {
        "prompt": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(sample)},
        ],
        "completion": [
            {"role": "assistant", "content": build_sft_completion(sample)},
        ],
        "label": sample.label,
        "battery_id": sample.battery_id,
        "process_ids": [process.process_id for process in sample.charging_process],
    }


def build_grpo_prompt_record(sample: BatterySample) -> dict[str, object]:
    return {
        "prompt": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(sample)},
        ],
        "label": sample.label,
        "battery_id": sample.battery_id,
        "process_ids": [process.process_id for process in sample.charging_process],
    }