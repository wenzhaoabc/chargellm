from __future__ import annotations

import json
from pathlib import Path

from torch.utils.data import Dataset

from chargellm.schemas.data_schema import BatterySample


class BatteryJsonDataset(Dataset):
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        with self.file_path.open("r", encoding="utf-8") as handle:
            raw_samples = json.load(handle)
        self.samples = [BatterySample.model_validate(sample) for sample in raw_samples]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> BatterySample:
        return self.samples[index]
