from __future__ import annotations

import json


def _parse_completion(completion: str) -> dict | None:
    try:
        return json.loads(completion)
    except json.JSONDecodeError:
        return None


def json_validity_reward(completions: list[str], **_: object) -> list[float]:
    return [1.0 if _parse_completion(completion) is not None else -1.0 for completion in completions]


def label_correctness_reward(completions: list[str], labels: list[str], **_: object) -> list[float]:
    rewards: list[float] = []
    for completion, label in zip(completions, labels, strict=False):
        parsed = _parse_completion(completion)
        if parsed is None:
            rewards.append(-1.0)
            continue
        rewards.append(1.0 if parsed.get("label") == label else -1.0)
    return rewards


def confidence_range_reward(completions: list[str], **_: object) -> list[float]:
    rewards: list[float] = []
    for completion in completions:
        parsed = _parse_completion(completion)
        if parsed is None:
            rewards.append(-1.0)
            continue
        confidence = parsed.get("confidence")
        valid = isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0
        rewards.append(0.5 if valid else -0.5)
    return rewards


def key_process_reward(completions: list[str], process_ids: list[list[str]], **_: object) -> list[float]:
    rewards: list[float] = []
    for completion, valid_process_ids in zip(completions, process_ids, strict=False):
        parsed = _parse_completion(completion)
        if parsed is None:
            rewards.append(-1.0)
            continue
        predicted = parsed.get("key_processes")
        if not isinstance(predicted, list) or not predicted:
            rewards.append(-0.5)
            continue
        all_valid = all(process_id in valid_process_ids for process_id in predicted)
        rewards.append(0.5 if all_valid else -0.5)
    return rewards
