from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_demo_session
from app.db.session import get_db
from app.models.demo_session import DemoSession
from app.schemas.battery import BatteryExampleRead, DatasetListResponse, DatasetUploadRequest
from app.services.battery_service import (
    create_dataset,
    delete_dataset,
    get_dataset_for_user,
    list_datasets_for_user,
    parse_dataset_content,
    serialize_dataset,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=DatasetListResponse)
def get_datasets(
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
) -> DatasetListResponse:
    items = [serialize_dataset(item) for item in list_datasets_for_user(db, session.user.id)]
    return DatasetListResponse(items=items)


@router.post("/upload", response_model=BatteryExampleRead)
def upload_dataset(
    payload: DatasetUploadRequest,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        series = parse_dataset_content(payload.file_name, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    dataset = create_dataset(
        db,
        title=payload.name,
        problem_type="用户导入数据",
        capacity_range="待诊断",
        description="客户侧自主导入的脱敏充电过程数据。",
        source="user_upload",
        owner_user_id=session.user.id,
        series=series,
    )
    return serialize_dataset(dataset)


@router.delete("/{dataset_id}")
def remove_user_dataset(
    dataset_id: int,
    session: DemoSession = Depends(require_demo_session),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    dataset = get_dataset_for_user(db, dataset_id, session.user.id)
    if dataset is None or dataset.source != "user_upload" or dataset.owner_user_id != session.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset_not_found")
    delete_dataset(db, dataset)
    return {"id": dataset_id, "status": "deleted"}
