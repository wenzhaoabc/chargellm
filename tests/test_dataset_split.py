from chargellm.schemas.data_schema import BatterySample


def test_battery_id_is_available_for_group_split() -> None:
    sample = BatterySample.model_validate(
        {
            "battery_id": "battery-001",
            "label": "正常",
            "charging_process": [
                {
                    "process_id": "p1",
                    "current_series": [1.0],
                    "voltage_series": [2.0],
                    "power_series": [3.0],
                    "charge_capacity": [4.0],
                }
            ],
        }
    )
    assert sample.battery_id == "battery-001"
