from __future__ import annotations

from app.services.charging_data_service import (
    _postprocess_series,
    _row_to_order,
    _split_floats,
    _split_ints,
)


def test_split_handles_empty_and_sentinel():
    assert _split_floats(None) == []
    assert _split_floats("") == []
    assert _split_floats("1.0,-1,2.5", missing_sentinel=-1.0) == [1.0, None, 2.5]
    assert _split_ints("0,5,10") == [0, 5, 10]
    assert _split_ints("0.0,5.0,10.0") == [0, 5, 10]


def test_postprocess_prepends_zero_when_first_push_time_nonzero():
    series = _postprocess_series([2, 5, 10], [50.0, 60.0, 70.0], [220.0, 221.0, 222.0], [1.0, 1.1, 1.2])
    assert series.time_offset_min == [0, 2, 5, 10]
    assert series.powers == [0.0, 50.0, 60.0, 70.0]
    assert series.voltages == [220.0, 220.0, 221.0, 222.0]
    assert series.currents == [0.0, 1.0, 1.1, 1.2]


def test_postprocess_keeps_zero_first_point():
    series = _postprocess_series([0, 5], [10.0, 20.0], [220.0, 221.0], [1.0, 2.0])
    assert series.time_offset_min == [0, 5]
    assert series.powers == [10.0, 20.0]


def test_postprocess_handles_missing_voltage():
    series = _postprocess_series([3, 8], [10.0, 20.0], [None, 222.0], [1.0, 2.0])
    assert series.time_offset_min == [0, 3, 8]
    # First non-None voltage is the "first known" value used as a stand-in
    assert series.voltages[0] == 222.0
    assert series.powers[0] == 0.0


def test_row_to_order_handles_mismatched_lengths():
    class FakeRow:
        _mapping = {
            "order_no": "ORD-1",
            "supplier_code": "S",
            "supplier_name": "供应商",
            "user_name": "张",
            "user_phone": "13000000000",
            "charge_start_time": "2026-01-01 10:00:00",
            "charge_end_time": "2026-01-01 11:00:00",
            "charge_capacity": 90.0,
            "push_times": "0,5,10,15",
            "powers": "10,20,30,40",
            "voltages": "220,221,222",  # one short
            "currents": "1,2,3,4",
        }

    order = _row_to_order(FakeRow())
    # Trimmed to shortest length (3)
    assert len(order.series.time_offset_min) == 3
    assert len(order.series.voltages) == 3
