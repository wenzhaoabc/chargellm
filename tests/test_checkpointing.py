from pathlib import Path

import torch
from torch import nn

from chargellm.training.common import save_wrapper_checkpoint


class FakeLlm(nn.Module):
    def save_pretrained(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        (path / "adapter_config.json").write_text("{}", encoding="utf-8")


class FakeModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.llm = FakeLlm()
        self.linear = nn.Linear(2, 2)

    def get_wrapper_state_dict(self):
        return {
            "linear.weight": self.linear.weight.detach().clone(),
            "linear.bias": self.linear.bias.detach().clone(),
        }


def test_save_wrapper_checkpoint(tmp_path) -> None:
    model = FakeModel()
    optimizer = torch.optim.AdamW(model.linear.parameters(), lr=1e-3)
    save_wrapper_checkpoint(tmp_path, model, optimizer, step=3)
    assert (tmp_path / "llm_adapter").exists()
    assert (tmp_path / "wrapper_state.pt").exists()
    assert (tmp_path / "trainer_state.pt").exists()