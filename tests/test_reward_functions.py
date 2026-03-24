from chargellm.rewards.grpo_rewards import confidence_range_reward
from chargellm.rewards.grpo_rewards import json_validity_reward
from chargellm.rewards.grpo_rewards import key_process_reward
from chargellm.rewards.grpo_rewards import label_correctness_reward


def test_json_validity_reward() -> None:
    rewards = json_validity_reward(["{}", "not-json"])
    assert rewards == [1.0, -1.0]


def test_label_correctness_reward() -> None:
    rewards = label_correctness_reward([
        '{"label": "正常", "confidence": 0.9, "key_processes": ["p1"], "explanation": "ok"}'
    ], ["正常"])
    assert rewards == [1.0]


def test_confidence_range_reward() -> None:
    rewards = confidence_range_reward([
        '{"label": "正常", "confidence": 0.8, "key_processes": ["p1"], "explanation": "ok"}'
    ])
    assert rewards == [0.5]


def test_key_process_reward() -> None:
    rewards = key_process_reward([
        '{"label": "正常", "confidence": 0.8, "key_processes": ["p1"], "explanation": "ok"}'
    ], [["p1", "p2"]])
    assert rewards == [0.5]
