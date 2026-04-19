from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.battery import BatteryExampleListResponse, BatteryExampleRead, BatterySeries, HistoryQueryRequest, HistoryQueryResponse
from app.services.battery_service import get_example, list_examples
from app.services.auth_service import mask_phone

router = APIRouter(prefix="/charge", tags=["charge"])


def _to_read(item) -> BatteryExampleRead:
    series = BatterySeries.model_validate(json.loads(item.payload_json))
    return BatteryExampleRead(
        id=item.id,
        sample_key=item.sample_key,
        title=item.title,
        problem_type=item.problem_type,
        capacity_range=item.capacity_range,
        description=item.description,
        sort_order=item.sort_order,
        series=series,
    )


@router.get("/examples", response_model=BatteryExampleListResponse)
def read_examples(db: Session = Depends(get_db)) -> BatteryExampleListResponse:
    items = list_examples(db)
    return BatteryExampleListResponse(items=[_to_read(item) for item in items])


@router.get("/examples/{sample_key}", response_model=BatteryExampleRead)
def read_example(sample_key: str, db: Session = Depends(get_db)) -> BatteryExampleRead:
    item = get_example(db, sample_key)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="example_not_found")
    return _to_read(item)


@router.post("/history/query", response_model=HistoryQueryResponse)
def query_history(payload: HistoryQueryRequest) -> HistoryQueryResponse:
    settings = get_settings()
    if payload.sms_code != settings.sms_mock_code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sms_code_invalid")
    return HistoryQueryResponse(phone_masked=mask_phone(payload.phone), records=[])
