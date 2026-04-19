from chargellm.data.collator import BatteryCollator
from chargellm.schemas.data_schema import BatterySample


def test_collator_shapes() -> None:
    samples = [
        BatterySample.model_validate(
            {
                "battery_id": "battery-001",
                "label": "正常",
                "reason": "状态稳定。",
                "charging_process": [
                    {
                        "process_id": "p1",
                        "current_series": [1.0, 2.0],
                        "voltage_series": [3.0, 4.0],
                        "power_series": [5.0, 6.0],
                        "charge_capacity": [7.0, 8.0],
                    }
                ],
            }
        )
    ]
    batch = BatteryCollator()(samples)
    assert tuple(batch.inputs.shape) == (1, 1, 2, 4)
    assert tuple(batch.process_mask.shape) == (1, 1, 2)
    assert tuple(batch.history_mask.shape) == (1, 1)
