from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "dataset"
SFT_PATH = OUTPUT_DIR / "synthetic_sft.json"
GRPO_PATH = OUTPUT_DIR / "synthetic_grpo.json"
ORIGIN_PATH = OUTPUT_DIR / "synthetic_origin.jsonl"
SEED = 20260325


@dataclass(slots=True)
class BatteryProfile:
    label: str
    process_count: int
    capacity_scale: float
    voltage_offset: float
    taper_start_ratio: float
    current_noise: float
    power_drop_ratio: float
    waviness: float


PROFILES = {
    "正常": BatteryProfile("正常", 6, 1.00, 0.0, 0.82, 0.015, 0.12, 0.010),
    "电池老化": BatteryProfile("电池老化", 7, 0.86, 1.8, 0.68, 0.020, 0.22, 0.015),
    "电池故障": BatteryProfile("电池故障", 6, 0.79, -2.2, 0.58, 0.050, 0.35, 0.040),
    "非标电池": BatteryProfile("非标电池", 6, 0.93, 7.2, 0.74, 0.030, 0.18, 0.025),
}


REASONS = {
    "正常": "最近多次充电过程整体平稳，恒流段与后段回落趋势一致，累计充电量变化正常，未见持续异常。",
    "电池老化": "最近多次充电过程出现一致性衰退，后段提前进入回落区，单位时间累计充电量下降，更符合老化特征。",
    "电池故障": "近期充电过程存在明显异常波动，后段功率衰减过快且个别过程出现异常抖动，表现出故障风险。",
    "非标电池": "多次充电过程整体偏离参考分布，电压平台和功率区间与常规样本不一致，但内部形态相对稳定，符合非标电池特征。",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _simulate_process(profile: BatteryProfile, rng: random.Random, start_time: datetime, process_index: int) -> dict:
    duration_minutes = rng.randint(120, 360)
    end_time = start_time + timedelta(minutes=duration_minutes)

    current_series: list[float] = []
    voltage_series: list[float] = []
    power_series: list[float] = []
    charge_capacity: list[float] = []

    base_current = rng.uniform(18.0, 34.0) * profile.capacity_scale
    start_voltage = rng.uniform(322.0, 336.0) + profile.voltage_offset
    end_voltage_target = rng.uniform(419.0, 431.0) + profile.voltage_offset
    accumulated_energy = 0.0

    for minute in range(duration_minutes):
        progress = minute / max(duration_minutes - 1, 1)
        taper_progress = max(0.0, (progress - profile.taper_start_ratio) / max(1e-6, 1.0 - profile.taper_start_ratio))
        taper_factor = 1.0 - taper_progress * (0.72 + profile.power_drop_ratio)
        oscillation = math.sin(progress * math.pi * 3.0) * profile.waviness
        fault_burst = 0.0
        if profile.label == "电池故障" and 0.55 < progress < 0.85:
            fault_burst = math.sin(progress * math.pi * 18.0) * 0.08

        current = base_current * taper_factor * (1.0 + oscillation + fault_burst)
        current += rng.gauss(0.0, base_current * profile.current_noise)
        current = _clamp(current, 2.5, 42.0)

        voltage_rise = (end_voltage_target - start_voltage) * (1.0 - math.exp(-3.4 * progress))
        voltage = start_voltage + voltage_rise
        if profile.label == "电池故障" and progress > 0.75:
            voltage -= 1.5 + 0.8 * math.sin(progress * math.pi * 12.0)
        voltage += rng.gauss(0.0, 0.35)
        voltage = _clamp(voltage, 300.0, 438.0)

        power = voltage * current / 1000.0
        accumulated_energy += power / 60.0

        current_series.append(round(current, 3))
        voltage_series.append(round(voltage, 3))
        power_series.append(round(power, 3))
        charge_capacity.append(round(accumulated_energy, 4))

    return {
        "process_id": f"process_{process_index + 1}",
        "charge_start_time": start_time.isoformat(timespec="minutes"),
        "charge_end_time": end_time.isoformat(timespec="minutes"),
        "current_series": current_series,
        "voltage_series": voltage_series,
        "power_series": power_series,
        "charge_capacity": charge_capacity,
    }


def _build_sample(label: str, sample_index: int, include_reason: bool) -> dict:
    label_offset = {"正常": 11, "电池老化": 23, "电池故障": 37, "非标电池": 53}[label]
    rng = random.Random(SEED + sample_index * 97 + label_offset)
    profile = PROFILES[label]
    base_start = datetime(2025, 1, 1, 8, 0) + timedelta(days=sample_index * 3)
    processes = []
    for process_index in range(profile.process_count):
        start_time = base_start + timedelta(days=process_index, minutes=rng.randint(0, 40))
        processes.append(_simulate_process(profile, rng, start_time, process_index))

    sample = {
        "battery_id": f"{label}-battery-{sample_index:03d}",
        "label": label,
        "charging_process": processes,
    }
    if include_reason:
        sample["reason"] = REASONS[label]
    return sample


def build_datasets() -> tuple[list[dict], list[dict]]:
    sft_samples: list[dict] = []
    grpo_samples: list[dict] = []
    ordered_labels = ["正常", "电池老化", "电池故障", "非标电池"]

    for repeat_index in range(3):
        for label_index, label in enumerate(ordered_labels):
            sample_id = repeat_index * len(ordered_labels) + label_index
            sft_samples.append(_build_sample(label, sample_id, include_reason=True))

    for repeat_index in range(4):
        for label_index, label in enumerate(ordered_labels):
            sample_id = 100 + repeat_index * len(ordered_labels) + label_index
            grpo_samples.append(_build_sample(label, sample_id, include_reason=False))

    return sft_samples, grpo_samples


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sft_samples, grpo_samples = build_datasets()
    SFT_PATH.write_text(json.dumps(sft_samples, ensure_ascii=False, indent=2), encoding="utf-8")
    GRPO_PATH.write_text(json.dumps(grpo_samples, ensure_ascii=False, indent=2), encoding="utf-8")
    with ORIGIN_PATH.open("w", encoding="utf-8") as handle:
        for sample in sft_samples + grpo_samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(json.dumps({
        "synthetic_sft": len(sft_samples),
        "synthetic_grpo": len(grpo_samples),
        "interval_minutes": 1,
        "duration_hours": [2, 6],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()