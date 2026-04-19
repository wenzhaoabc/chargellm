from __future__ import annotations

import argparse
import json

import torch

from chargellm.config import DEFAULT_MAX_LENGTH
from chargellm.config import DEFAULT_MODEL_NAME_OR_PATH
from chargellm.config import DEFAULT_TS_HIDDEN_SIZE
from chargellm.data.ts_qwen_collator import TSQwenGRPOCollator
from chargellm.data.dataset import BatteryJsonDataset
from chargellm.training.common import load_tsqwen_checkpoint
from chargellm.schemas.output_schema import DiagnosisOutput


def _parse_diagnosis(text: str, process_ids: list[str]) -> DiagnosisOutput:
    try:
        payload = json.loads(text)
        return DiagnosisOutput.model_validate(payload)
    except Exception:
        return DiagnosisOutput(
            label="正常",
            confidence=0.0,
            key_processes=process_ids[:1] or ["unknown"],
            explanation=text.strip() or "模型未返回可解析 JSON。",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a demo inference for ChargeLLM.")
    parser.add_argument("--data-path", default="dataset/sft.json")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL_NAME_OR_PATH)
    parser.add_argument("--checkpoint-dir", default="artifacts/sft-smoke")
    parser.add_argument("--ts-hidden-size", type=int, default=None)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    args = parser.parse_args()

    dataset = BatteryJsonDataset(args.data_path)
    sample = dataset[args.index]
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else None
    model, _ = load_tsqwen_checkpoint(
        model_name_or_path=args.model_name_or_path,
        checkpoint_dir=args.checkpoint_dir,
        ts_hidden_size=args.ts_hidden_size,
        dtype=dtype,
        device_map=None,
        is_trainable=False,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    batch = TSQwenGRPOCollator(model.tokenizer, max_length=args.max_length)([sample])
    batch.timeseries.inputs = batch.timeseries.inputs.to(device)
    batch.timeseries.process_mask = batch.timeseries.process_mask.to(device)
    batch.timeseries.history_mask = batch.timeseries.history_mask.to(device)
    batch.input_ids = batch.input_ids.to(device)
    batch.attention_mask = batch.attention_mask.to(device)

    with torch.no_grad():
        generated_ids = model.generate(
            inputs=batch.timeseries.inputs,
            process_mask=batch.timeseries.process_mask,
            history_mask=batch.timeseries.history_mask,
            input_ids=batch.input_ids,
            attention_mask=batch.attention_mask,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
        )

    prompt_length = batch.input_ids.shape[1]
    completion_text = model.tokenizer.batch_decode(
        generated_ids[:, prompt_length:],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    result = _parse_diagnosis(completion_text, batch.timeseries.process_ids[0])
    print(json.dumps(result.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    main()