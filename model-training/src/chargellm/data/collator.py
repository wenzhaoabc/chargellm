from __future__ import annotations

from dataclasses import dataclass

import torch

from chargellm.schemas.data_schema import BatterySample, LABEL_TO_ID


@dataclass(slots=True)
class BatteryBatch:
    battery_ids: list[str]
    process_ids: list[list[str]]
    inputs: torch.Tensor
    process_mask: torch.Tensor
    history_mask: torch.Tensor
    labels: torch.Tensor
    reasons: list[str]


class BatteryCollator:
    def __call__(self, samples: list[BatterySample]) -> BatteryBatch:
        batch_size = len(samples)
        max_processes = max(len(sample.charging_process) for sample in samples)
        max_seq_len = max(
            max(len(process.current_series) for process in sample.charging_process)
            for sample in samples
        )

        inputs = torch.zeros(batch_size, max_processes, max_seq_len, 4, dtype=torch.float32)
        process_mask = torch.zeros(batch_size, max_processes, max_seq_len, dtype=torch.bool)
        history_mask = torch.zeros(batch_size, max_processes, dtype=torch.bool)

        battery_ids: list[str] = []
        process_ids: list[list[str]] = []
        labels: list[int] = []
        reasons: list[str] = []

        for batch_index, sample in enumerate(samples):
            battery_ids.append(sample.battery_id)
            process_ids.append([process.process_id for process in sample.charging_process])
            labels.append(LABEL_TO_ID[sample.label])
            reasons.append(sample.reason or "")

            for process_index, process in enumerate(sample.charging_process):
                history_mask[batch_index, process_index] = True
                seq_len = len(process.current_series)
                process_mask[batch_index, process_index, :seq_len] = True
                stacked = torch.tensor(
                    list(
                        zip(
                            process.current_series,
                            process.voltage_series,
                            process.power_series,
                            process.charge_capacity,
                            strict=False,
                        )
                    ),
                    dtype=torch.float32,
                )
                inputs[batch_index, process_index, :seq_len] = stacked

        return BatteryBatch(
            battery_ids=battery_ids,
            process_ids=process_ids,
            inputs=inputs,
            process_mask=process_mask,
            history_mask=history_mask,
            labels=torch.tensor(labels, dtype=torch.long),
            reasons=reasons,
        )
