# Suggested Commands

Environment setup:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Run tests:
```bash
pytest
```

Preview SFT data:
```bash
python -m chargellm.training.train_sft --dataset-view --data-path dataset/sft.json --model-name-or-path models/Qwen3-0.6B
```

Generate synthetic data:
```bash
python scripts/generate_synthetic_data.py
```

One-step SFT smoke training:
```bash
python -m chargellm.training.train_sft --train --data-path dataset/sft.json --model-name-or-path models/Qwen3-0.6B --output-dir artifacts/sft-smoke --batch-size 1 --epochs 1 --max-steps 1
```

One-step GRPO smoke training from SFT checkpoint:
```bash
python -m chargellm.training.train_grpo --train --data-path dataset/grpo.json --model-name-or-path models/Qwen3-0.6B --checkpoint-dir artifacts/sft-smoke --output-dir artifacts/grpo-smoke --batch-size 1 --epochs 1 --max-steps 1
```

Demo inference:
```bash
python -m chargellm.inference.infer_demo --data-path dataset/sft.json --index 0 --model-name-or-path models/Qwen3-0.6B --checkpoint-dir artifacts/sft-smoke
```

Useful Linux commands for navigation/search:
```bash
git status
rg "pattern" src tests
ls
cd /root/autodl-tmp/tr/chargellm
```

Note: project instructions prefer Serena MCP for code/file search and `apply_patch` for edits.