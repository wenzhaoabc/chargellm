import torch

from chargellm.models.joint_model import JointDiagnosisModel


def test_joint_model_forward_runs() -> None:
    model = JointDiagnosisModel(hidden_size=32, llm_hidden_size=64, num_labels=4)
    inputs = torch.randn(2, 3, 5, 4)
    process_mask = torch.ones(2, 3, 5, dtype=torch.bool)
    history_mask = torch.ones(2, 3, dtype=torch.bool)
    labels = torch.tensor([0, 1], dtype=torch.long)
    outputs = model(inputs, process_mask, history_mask, labels)
    assert tuple(outputs["logits"].shape) == (2, 4)
    assert tuple(outputs["confidence"].shape) == (2,)
    assert tuple(outputs["prefix_embeddings"].shape) == (2, 8, 64)
    assert "loss" in outputs
