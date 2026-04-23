from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_demo_session
from app.core.config import get_settings
from app.core.security import mask_phone
from app.db.session import get_db
from app.models.demo_session import DemoSession
from app.schemas.battery import BatteryExampleListResponse, BatteryExampleRead, BatterySeries, HistoryQueryRequest, HistoryQueryResponse
from app.schemas.charge_order import ChargeOrderListResponse, ChargeOrderQueryRequest, ChargeOrderRead
from app.services.battery_service import get_example, list_examples
from app.services.charging_data_service import query_charge_orders_by_phone

logger = logging.getLogger(__name__)

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


@router.post("/orders", response_model=ChargeOrderListResponse)
def query_user_orders(
    payload: ChargeOrderQueryRequest,
    _: DemoSession = Depends(require_demo_session),
) -> ChargeOrderListResponse:
    """Return *all* completed charge orders for a user phone within a time window.

    Designed to be called either directly by the frontend (PhoneSearchPanel) or
    by the LLM via the `query_charging_records` tool. The full batch is
    intended to be fed to the model for cross-order analysis.
    """
    settings = get_settings()
    if not settings.iot_db_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="iot_db_not_configured")
    try:
        orders = query_charge_orders_by_phone(
            payload.phone,
            start_time=payload.start_time.replace(tzinfo=None) if payload.start_time else None,
            end_time=payload.end_time.replace(tzinfo=None) if payload.end_time else None,
            settings=settings,
        )
    except SQLAlchemyError as exc:
        logger.exception("charge order query failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="iot_db_query_failed") from exc
    return ChargeOrderListResponse(
        phone_masked=mask_phone(payload.phone),
        orders=[ChargeOrderRead.model_validate(order.to_dict()) for order in orders],
    )


@router.post("/history/query", response_model=HistoryQueryResponse)
def query_history(payload: HistoryQueryRequest) -> HistoryQueryResponse:
    """Legacy endpoint kept for backward compat; prefer POST /charge/orders."""
    settings = get_settings()
    if payload.sms_code != settings.sms_mock_code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sms_code_invalid")
    return HistoryQueryResponse(phone_masked=mask_phone(payload.phone), records=[])

