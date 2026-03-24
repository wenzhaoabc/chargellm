from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch

from chargellm.models.qwen_joint_model import TSQwenForDiagnosis


@dataclass(slots=True)
class TrainMetrics:
    loss: float
    lm_loss: float
    classification_loss: float


@dataclass(slots=True)
class GrpoMetrics:
    loss: float
    mean_reward: float
    mean_advantage: float


def move_batch_to_device(batch, device: torch.device):
    batch.timeseries.inputs = batch.timeseries.inputs.to(device)
    batch.timeseries.process_mask = batch.timeseries.process_mask.to(device)
    batch.timeseries.history_mask = batch.timeseries.history_mask.to(device)
    batch.timeseries.labels = batch.timeseries.labels.to(device)
    batch.input_ids = batch.input_ids.to(device)
    batch.attention_mask = batch.attention_mask.to(device)
    batch.class_labels = batch.class_labels.to(device)
    if batch.lm_labels is not None:
        batch.lm_labels = batch.lm_labels.to(device)
    return batch


def save_wrapper_checkpoint(output_dir: str | Path, model, optimizer: torch.optim.Optimizer, step: int) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    llm_path = output_path / "llm_adapter"
    if hasattr(model.llm, "save_pretrained"):
        model.llm.save_pretrained(llm_path)
    torch.save(model.get_wrapper_state_dict(), output_path / "wrapper_state.pt")
    torch.save({"optimizer": optimizer.state_dict(), "step": step}, output_path / "trainer_state.pt")


def infer_wrapper_dimensions(checkpoint_dir: str | Path) -> tuple[int, int]:
    wrapper_state_path = Path(checkpoint_dir) / "wrapper_state.pt"
    wrapper_state = torch.load(wrapper_state_path, map_location="cpu")
    label_weight = wrapper_state["label_head.weight"]
    return int(label_weight.shape[1]), int(label_weight.shape[0])


def load_tsqwen_checkpoint(
    model_name_or_path: str,
    checkpoint_dir: str | Path,
    ts_hidden_size: int | None,
    num_labels: int | None = None,
    dtype: torch.dtype | None = None,
    device_map: str | dict[str, int] | None = None,
    is_trainable: bool = False,
):
    checkpoint_path = Path(checkpoint_dir)
    if ts_hidden_size is None or num_labels is None:
        inferred_hidden_size, inferred_num_labels = infer_wrapper_dimensions(checkpoint_path)
        if ts_hidden_size is None:
            ts_hidden_size = inferred_hidden_size
        if num_labels is None:
            num_labels = inferred_num_labels
    model = TSQwenForDiagnosis.from_checkpoint(
        model_name=model_name_or_path,
        checkpoint_dir=str(checkpoint_path),
        ts_hidden_size=ts_hidden_size,
        num_labels=num_labels,
        dtype=dtype,
        device_map=device_map,
        is_trainable=is_trainable,
    )
    trainer_state_path = checkpoint_path / "trainer_state.pt"
    trainer_state = None
    if trainer_state_path.exists():
        trainer_state = torch.load(trainer_state_path, map_location="cpu")
    return model, trainer_state