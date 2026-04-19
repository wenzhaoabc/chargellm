from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import torch
from torch.nn.utils import clip_grad_norm_
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm

from chargellm.config import DEFAULT_MAX_LENGTH
from chargellm.config import DEFAULT_MODEL_NAME_OR_PATH
from chargellm.config import DEFAULT_TS_HIDDEN_SIZE
from chargellm.data.hf_builders import build_sft_hf_dataset
from chargellm.data.ts_qwen_collator import TSQwenSFTCollator
from chargellm.data.dataset import BatteryJsonDataset
from chargellm.llm.prompting import build_sft_prompt_record
from chargellm.models.qwen_joint_model import TSQwenForDiagnosis
from chargellm.training.common import TrainMetrics
from chargellm.training.common import move_batch_to_device
from chargellm.training.common import save_wrapper_checkpoint


def build_sft_preview(file_path: str | Path) -> list[dict[str, str]]:
    dataset = BatteryJsonDataset(file_path)
    previews: list[dict[str, str]] = []
    for sample in dataset:
        record = build_sft_prompt_record(sample)
        prompt = json.dumps(record["prompt"], ensure_ascii=False)
        completion = record["completion"][0]["content"]
        previews.append({"prompt": prompt, "completion": completion})
    return previews


def build_sft_dataset_preview(file_path: str | Path) -> list[dict[str, object]]:
    dataset = build_sft_hf_dataset(str(file_path))
    return [dataset[index] for index in range(len(dataset))]


def train_sft(
    data_path: str,
    model_name_or_path: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    max_length: int,
    ts_hidden_size: int,
    classification_loss_weight: float,
    max_steps: int | None,
) -> TrainMetrics:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_dtype = None
    scaler_enabled = False
    if device.type == "cuda":
        if torch.cuda.is_bf16_supported():
            amp_dtype = torch.bfloat16
        else:
            amp_dtype = torch.float16
            scaler_enabled = True
    model = TSQwenForDiagnosis.from_pretrained(
        model_name=model_name_or_path,
        ts_hidden_size=ts_hidden_size,
        use_lora=True,
        dtype=amp_dtype,
        device_map=None,
    )
    model.to(device)
    model.train()

    dataset = BatteryJsonDataset(data_path)
    collator = TSQwenSFTCollator(model.tokenizer, max_length=max_length)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=collator)

    optimizer = AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=learning_rate)
    scaler = torch.amp.GradScaler("cuda", enabled=scaler_enabled)
    global_step = 0
    last_metrics = TrainMetrics(loss=0.0, lm_loss=0.0, classification_loss=0.0)

    for _ in range(epochs):
        for batch in tqdm(dataloader, desc="sft-train", leave=False):
            batch = move_batch_to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=amp_dtype is not None):
                outputs = model(
                    inputs=batch.timeseries.inputs,
                    process_mask=batch.timeseries.process_mask,
                    history_mask=batch.timeseries.history_mask,
                    input_ids=batch.input_ids,
                    attention_mask=batch.attention_mask,
                    lm_labels=batch.lm_labels,
                    class_labels=batch.class_labels,
                )
                lm_loss = outputs["lm_outputs"].loss
                classification_loss = outputs.get("classification_loss", torch.tensor(0.0, device=device))
                total_loss = lm_loss + classification_loss_weight * classification_loss

            if scaler_enabled:
                scaler.scale(total_loss).backward()
                scaler.unscale_(optimizer)
                clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                total_loss.backward()
                clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            global_step += 1
            last_metrics = TrainMetrics(
                loss=float(total_loss.detach().item()),
                lm_loss=float(lm_loss.detach().item()),
                classification_loss=float(classification_loss.detach().item()),
            )
            if max_steps is not None and global_step >= max_steps:
                save_wrapper_checkpoint(output_dir, model, optimizer, global_step)
                return last_metrics

    save_wrapper_checkpoint(output_dir, model, optimizer, global_step)
    return last_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SFT preview data for ChargeLLM.")
    parser.add_argument("--data-path", default="dataset/sft.json")
    parser.add_argument("--preview-count", type=int, default=2)
    parser.add_argument("--dataset-view", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL_NAME_OR_PATH)
    parser.add_argument("--output-dir", default="artifacts/sft")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--ts-hidden-size", type=int, default=DEFAULT_TS_HIDDEN_SIZE)
    parser.add_argument("--classification-loss-weight", type=float, default=0.2)
    parser.add_argument("--max-steps", type=int, default=None)
    args = parser.parse_args()

    if args.train:
        metrics = train_sft(
            data_path=args.data_path,
            model_name_or_path=args.model_name_or_path,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_length=args.max_length,
            ts_hidden_size=args.ts_hidden_size,
            classification_loss_weight=args.classification_loss_weight,
            max_steps=args.max_steps,
        )
        print(json.dumps(asdict(metrics), ensure_ascii=False))
        return

    previews = build_sft_dataset_preview(args.data_path) if args.dataset_view else build_sft_preview(args.data_path)
    for item in previews[: args.preview_count]:
        print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()