import torch

from chargellm.training.train_grpo import _build_lm_labels
from chargellm.training.train_grpo import _sum_rewards


def test_sum_rewards_returns_tensor() -> None:
    rewards = _sum_rewards(
        completions=['{"label":"正常","confidence":0.5,"key_processes":["p1"],"explanation":"ok"}'],
        labels=["正常"],
        process_ids=[["p1"]],
    )
    assert isinstance(rewards, torch.Tensor)
    assert rewards.shape == (1,)


def test_build_lm_labels_masks_prompt() -> None:
    input_ids = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    labels = _build_lm_labels(input_ids, prompt_length=2)
    assert labels.tolist() == [[-100, -100, 3, 4]]