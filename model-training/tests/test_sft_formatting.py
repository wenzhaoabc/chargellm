from chargellm.training.train_sft import build_sft_preview


def test_sft_preview_contains_prompt_and_completion() -> None:
    previews = build_sft_preview("dataset/sft.json")
    assert previews
    assert "prompt" in previews[0]
    assert "completion" in previews[0]
