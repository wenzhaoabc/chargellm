import torch

from chargellm.models.qwen_joint_model import TSQwenForDiagnosis


def test_prepare_inputs_embeds_shapes() -> None:
    prefix_embeddings = torch.randn(2, 3, 8)
    text_embeddings = torch.randn(2, 5, 8)
    attention_mask = torch.ones(2, 5, dtype=torch.long)
    labels = torch.tensor([[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]], dtype=torch.long)

    prepared = TSQwenForDiagnosis.prepare_inputs_embeds(
        prefix_embeddings=prefix_embeddings,
        text_embeddings=text_embeddings,
        attention_mask=attention_mask,
        labels=labels,
    )

    assert tuple(prepared.inputs_embeds.shape) == (2, 8, 8)
    assert tuple(prepared.attention_mask.shape) == (2, 8)
    assert tuple(prepared.labels.shape) == (2, 8)
    assert torch.all(prepared.labels[:, :3] == -100)