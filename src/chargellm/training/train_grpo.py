from __future__ import annotations

import argparse
from dataclasses import asdict
import json

import torch
from torch.nn.utils import clip_grad_norm_
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm

from chargellm.config import DEFAULT_MAX_LENGTH
from chargellm.config import DEFAULT_MODEL_NAME_OR_PATH
from chargellm.config import DEFAULT_TS_HIDDEN_SIZE
from chargellm.data.hf_builders import build_grpo_hf_dataset
from chargellm.data.ts_qwen_collator import TSQwenGRPOCollator
from chargellm.data.dataset import BatteryJsonDataset
from chargellm.llm.prompting import build_grpo_prompt_record
from chargellm.schemas.data_schema import LABELS
from chargellm.training.common import GrpoMetrics
from chargellm.training.common import load_tsqwen_checkpoint
from chargellm.training.common import move_batch_to_device
from chargellm.training.common import save_wrapper_checkpoint
from chargellm.rewards.grpo_rewards import confidence_range_reward
from chargellm.rewards.grpo_rewards import json_validity_reward
from chargellm.rewards.grpo_rewards import key_process_reward
from chargellm.rewards.grpo_rewards import label_correctness_reward


def build_mock_completion(label: str, process_ids: list[str]) -> str:
    return json.dumps(
        {
            "label": label,
            "confidence": 0.75,
            "key_processes": process_ids[:1] or ["unknown"],
            "explanation": "模型根据历史充电过程给出诊断结论。",
        },
        ensure_ascii=False,
    )


def _sum_rewards(completions: list[str], labels: list[str], process_ids: list[list[str]]) -> torch.Tensor:
    reward_terms = [
        torch.tensor(json_validity_reward(completions), dtype=torch.float32),
        torch.tensor(label_correctness_reward(completions, labels), dtype=torch.float32),
        torch.tensor(confidence_range_reward(completions), dtype=torch.float32),
        torch.tensor(key_process_reward(completions, process_ids), dtype=torch.float32),
    ]
    return sum(reward_terms)


def _build_lm_labels(input_ids: torch.Tensor, prompt_length: int) -> torch.Tensor:
    labels = input_ids.clone()
    labels[:, :prompt_length] = -100
    return labels


def train_grpo(
    data_path: str,
    model_name_or_path: str,
    checkpoint_dir: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    max_length: int,
    ts_hidden_size: int | None,
    max_steps: int | None,
    num_generations: int,
    max_new_tokens: int,
    temperature: float,
) -> GrpoMetrics:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_dtype = None
    scaler_enabled = False
    if device.type == "cuda":
        if torch.cuda.is_bf16_supported():
            amp_dtype = torch.bfloat16
        else:
            amp_dtype = torch.float16
            scaler_enabled = True

    model, _ = load_tsqwen_checkpoint(
        model_name_or_path=model_name_or_path,
        checkpoint_dir=checkpoint_dir,
        ts_hidden_size=ts_hidden_size,
        dtype=amp_dtype,
        device_map=None,
        is_trainable=True,
    )
    model.to(device)
    model.train()

    dataset = BatteryJsonDataset(data_path)
    collator = TSQwenGRPOCollator(model.tokenizer, max_length=max_length)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=collator)
    optimizer = AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=learning_rate)
    scaler = torch.amp.GradScaler("cuda", enabled=scaler_enabled)
    global_step = 0
    last_metrics = GrpoMetrics(loss=0.0, mean_reward=0.0, mean_advantage=0.0)

    for _ in range(epochs):
        for batch in tqdm(dataloader, desc="grpo-train", leave=False):
            batch = move_batch_to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            sample_losses: list[torch.Tensor] = []
            rewards_buffer: list[float] = []
            advantages_buffer: list[float] = []

            for sample_index in range(batch.input_ids.size(0)):
                sample_prompt_ids = batch.input_ids[sample_index : sample_index + 1]
                sample_prompt_mask = batch.attention_mask[sample_index : sample_index + 1]
                sample_inputs = batch.timeseries.inputs[sample_index : sample_index + 1]
                sample_process_mask = batch.timeseries.process_mask[sample_index : sample_index + 1]
                sample_history_mask = batch.timeseries.history_mask[sample_index : sample_index + 1]
                repeated_inputs = sample_inputs.repeat(num_generations, 1, 1, 1)
                repeated_process_mask = sample_process_mask.repeat(num_generations, 1, 1)
                repeated_history_mask = sample_history_mask.repeat(num_generations, 1)
                repeated_prompt_ids = sample_prompt_ids.repeat(num_generations, 1)
                repeated_prompt_mask = sample_prompt_mask.repeat(num_generations, 1)

                with torch.no_grad():
                    generated_ids = model.generate(
                        inputs=repeated_inputs,
                        process_mask=repeated_process_mask,
                        history_mask=repeated_history_mask,
                        input_ids=repeated_prompt_ids,
                        attention_mask=repeated_prompt_mask,
                        max_new_tokens=max_new_tokens,
                        do_sample=True,
                        temperature=temperature,
                    )

                prompt_length = sample_prompt_ids.size(1)
                completion_ids = generated_ids[:, prompt_length:]
                completions = model.tokenizer.batch_decode(
                    completion_ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
                label_text = LABELS[int(batch.class_labels[sample_index].item())]
                rewards = _sum_rewards(
                    completions=completions,
                    labels=[label_text] * num_generations,
                    process_ids=[batch.timeseries.process_ids[sample_index]] * num_generations,
                ).to(device)
                advantages = (rewards - rewards.mean()) / rewards.std(unbiased=False).clamp_min(1e-6)
                lm_labels = _build_lm_labels(generated_ids, prompt_length)
                generated_attention_mask = generated_ids.ne(model.tokenizer.pad_token_id).long()

                with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=amp_dtype is not None):
                    sequence_log_probs = model.sequence_log_probs(
                        inputs=repeated_inputs,
                        process_mask=repeated_process_mask,
                        history_mask=repeated_history_mask,
                        input_ids=generated_ids,
                        attention_mask=generated_attention_mask,
                        lm_labels=lm_labels,
                    )
                    sample_loss = -(advantages * sequence_log_probs).mean()

                sample_losses.append(sample_loss)
                rewards_buffer.extend(rewards.detach().cpu().tolist())
                advantages_buffer.extend(advantages.detach().cpu().tolist())

            total_loss = torch.stack(sample_losses).mean()
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
            last_metrics = GrpoMetrics(
                loss=float(total_loss.detach().item()),
                mean_reward=float(sum(rewards_buffer) / max(len(rewards_buffer), 1)),
                mean_advantage=float(sum(advantages_buffer) / max(len(advantages_buffer), 1)),
            )
            if max_steps is not None and global_step >= max_steps:
                save_wrapper_checkpoint(output_dir, model, optimizer, global_step)
                return last_metrics

    save_wrapper_checkpoint(output_dir, model, optimizer, global_step)
    return last_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview GRPO rewards for ChargeLLM.")
    parser.add_argument("--data-path", default="dataset/grpo.json")
    parser.add_argument("--dataset-view", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL_NAME_OR_PATH)
    parser.add_argument("--checkpoint-dir", default="artifacts/sft-smoke")
    parser.add_argument("--output-dir", default="artifacts/grpo")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--ts-hidden-size", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--num-generations", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.8)
    args = parser.parse_args()

    if args.dataset_view:
        dataset = build_grpo_hf_dataset(args.data_path)
        for index in range(len(dataset)):
            print(json.dumps(dataset[index], ensure_ascii=False))
        return

    if args.train:
        metrics = train_grpo(
            data_path=args.data_path,
            model_name_or_path=args.model_name_or_path,
            checkpoint_dir=args.checkpoint_dir,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_length=args.max_length,
            ts_hidden_size=args.ts_hidden_size,
            max_steps=args.max_steps,
            num_generations=args.num_generations,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        print(json.dumps(asdict(metrics), ensure_ascii=False))
        return

    dataset = BatteryJsonDataset(args.data_path)
    completions: list[str] = []
    labels: list[str] = []
    process_ids: list[list[str]] = []

    for sample in dataset:
        ids = [process.process_id for process in sample.charging_process]
        completions.append(build_mock_completion(sample.label, ids))
        labels.append(sample.label)
        process_ids.append(ids)
        _ = build_grpo_prompt_record(sample)

    rewards = {
        "json_validity": json_validity_reward(completions),
        "label_correctness": label_correctness_reward(completions, labels),
        "confidence_range": confidence_range_reward(completions),
        "key_process": key_process_reward(completions, process_ids),
    }
    print(json.dumps(rewards, ensure_ascii=False))


if __name__ == "__main__":
    main()