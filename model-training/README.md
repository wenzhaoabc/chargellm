# ChargeLLM Model Training

AI 模型训练项目，负责电动自行车电池健康诊断大模型的数据契约、时序特征建模、结构化诊断、SFT、GRPO 和离线推理验证。

Battery diagnosis with a TS-LLM pipeline for charging-history understanding, structured diagnosis, SFT, and GRPO.

基于时序编码与LLM的面向电池充电历史理解、结构化诊断的 TS-LLM 项目。

## Readme

- 中文文档: [README.zh-CN.md](README.zh-CN.md)
- English documentation: [README.en.md](README.en.md)

## Quick Start

1. Create a Python environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

2. Prepare a local Qwen checkpoint directory and pass it explicitly when running training or inference.

```bash
python -m chargellm.training.train_sft --dataset-view --data-path dataset/sft.json --model-name-or-path models/Qwen3-0.6B
```

3. Run the test suite.

```bash
pytest
```

4. Optionally generate additional synthetic datasets.

```bash
python scripts/generate_synthetic_data.py
```

5. Run a one-step SFT smoke training.

```bash
python -m chargellm.training.train_sft \
	--train \
	--data-path dataset/sft.json \
	--model-name-or-path models/Qwen3-0.6B \
	--output-dir artifacts/sft-smoke \
	--batch-size 1 \
	--epochs 1 \
	--max-steps 1
```

6. Run a one-step GRPO smoke training from the SFT checkpoint.

```bash
python -m chargellm.training.train_grpo \
	--train \
	--data-path dataset/grpo.json \
	--model-name-or-path models/Qwen3-0.6B \
	--checkpoint-dir artifacts/sft-smoke \
	--output-dir artifacts/grpo-smoke \
	--batch-size 1 \
	--epochs 1 \
	--max-steps 1
```

7. Run demo inference with the saved checkpoint.

```bash
python -m chargellm.inference.infer_demo \
	--data-path dataset/sft.json \
	--index 0 \
	--model-name-or-path models/Qwen3-0.6B \
	--checkpoint-dir artifacts/sft-smoke
```

## Quick Links

- Architecture: [docs/architecture.md](docs/architecture.md)
- Data contract: [docs/data_contract.md](docs/data_contract.md)
- SFT and GRPO plan: [docs/sft_grpo_plan.md](docs/sft_grpo_plan.md)
- Testing strategy: [docs/testing_strategy.md](docs/testing_strategy.md)

## Datasets

- Base SFT samples: `dataset/sft.json`
- Base GRPO samples: `dataset/grpo.json`
- Synthetic SFT samples: `dataset/synthetic_sft.json`
- Synthetic GRPO samples: `dataset/synthetic_grpo.json`
- Synthetic raw jsonl: `dataset/synthetic_origin.jsonl`

## Synthetic Data

Generate synthetic battery charging histories with:

```bash
python scripts/generate_synthetic_data.py
```

The generated data satisfies:

- 2 to 6 hours per charging process
- 1-minute sampling interval
- coherent current, voltage, power, and cumulative charge trajectories
- battery-level labels with multi-process histories

