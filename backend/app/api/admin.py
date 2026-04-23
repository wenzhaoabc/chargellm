from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import mask_phone
from app.db.session import get_db
from app.models.admin_content import SystemPrompt, WelcomeMessage
from app.models.battery import BatteryExample
from app.models.invite import InviteCode
from app.models.user import User
from app.schemas.admin_content import (
    AdminConversationDetail,
    AdminConversationListResponse,
    AdminConversationRead,
    AdminUserListResponse,
    AdminUserRead,
    AdminUserUpdateRequest,
    SystemPromptCreateRequest,
    SystemPromptRead,
    SystemPromptUpdateRequest,
    WelcomeMessageCreateRequest,
    WelcomeMessageRead,
    WelcomeMessageUpdateRequest,
)
from app.schemas.auth import (
    AdminMeResponse,
    InviteCodeCreateRequest,
    InviteCodeDeleteResponse,
    InviteCodeRead,
    InviteCodeUpdateRequest,
)
from app.schemas.battery import (
    AdminDatasetCreateRequest,
    AdminDatasetUpdateRequest,
    BatteryExampleRead,
    DatasetDeleteResponse,
    MysqlDatasetImportRequest,
)
from app.services.admin_content_service import (
    create_system_prompt,
    create_welcome_message,
    delete_system_prompt,
    delete_welcome_message,
    list_system_prompts,
    list_welcome_messages,
    update_system_prompt,
    update_welcome_message,
)
from app.services.battery_service import (
    create_dataset,
    delete_dataset,
    import_dataset_from_mysql,
    list_admin_datasets,
    parse_dataset_content,
    serialize_dataset,
    update_dataset,
)
from app.services.chat_history_service import get_conversation_detail, list_admin_conversations
from app.services.invite_service import create_invite, list_invites, update_invite

router = APIRouter(prefix="/admin", tags=["admin"])
bearer_scheme = HTTPBearer(auto_error=False)


def require_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_token_missing")
    token = credentials.credentials
    if token not in request.app.state.admin_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_token_invalid")
    return token


@router.get("/me", response_model=AdminMeResponse)
def admin_me(request: Request, admin_token: str = Depends(require_admin_token)) -> AdminMeResponse:
    _ = admin_token
    return AdminMeResponse(username=request.app.state.admin_username)


@router.get("/invites", response_model=list[InviteCodeRead])
def get_invites(_: str = Depends(require_admin_token), db: Session = Depends(get_db)) -> list[InviteCodeRead]:
    invites = list_invites(db)
    return [
        InviteCodeRead(
            id=item.id,
            code=item.code,
            name=item.name,
            max_uses=item.max_uses,
            used_uses=item.used_uses,
            per_user_quota=item.per_user_quota,
            expires_at=item.expires_at,
            is_active=item.is_active,
        )
        for item in invites
    ]


@router.post("/invites", response_model=InviteCodeRead)
def create_invite_route(
    payload: InviteCodeCreateRequest,
    request: Request,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> InviteCodeRead:
    settings = request.app.state.settings
    invite = create_invite(
        db,
        settings,
        name=payload.name,
        code=payload.code,
        max_uses=payload.max_uses,
        per_user_quota=payload.per_user_quota,
        expires_at=payload.expires_at,
    )
    return InviteCodeRead(
        id=invite.id,
        code=invite.code,
        name=invite.name,
        max_uses=invite.max_uses,
        used_uses=invite.used_uses,
        per_user_quota=invite.per_user_quota,
        expires_at=invite.expires_at,
        is_active=invite.is_active,
    )


@router.patch("/invites/{invite_id}", response_model=InviteCodeRead)
def update_invite_route(
    invite_id: int,
    payload: InviteCodeUpdateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> InviteCodeRead:
    invite = db.get(InviteCode, invite_id)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invite_not_found")
    invite = update_invite(db, invite, **payload.model_dump(exclude_unset=True))
    return InviteCodeRead(
        id=invite.id,
        code=invite.code,
        name=invite.name,
        max_uses=invite.max_uses,
        used_uses=invite.used_uses,
        per_user_quota=invite.per_user_quota,
        expires_at=invite.expires_at,
        is_active=invite.is_active,
    )


@router.delete("/invites/{invite_id}", response_model=InviteCodeDeleteResponse)
def delete_invite_route(
    invite_id: int,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> InviteCodeDeleteResponse:
    invite = db.get(InviteCode, invite_id)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invite_not_found")

    code = invite.code
    db.delete(invite)
    db.commit()
    return InviteCodeDeleteResponse(id=invite_id, code=code, status="deleted")


@router.get("/datasets", response_model=list[BatteryExampleRead])
def get_admin_datasets(_: str = Depends(require_admin_token), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [serialize_dataset(item) for item in list_admin_datasets(db)]


@router.post("/datasets", response_model=BatteryExampleRead)
def create_admin_dataset(
    payload: AdminDatasetCreateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if payload.content is None:
        series = {
            "time_offset_min": [0.0, 10.0, 20.0],
            "voltage_series": [48.0, 48.6, 49.0],
            "current_series": [8.0, 7.5, 6.8],
            "power_series": [384.0, 364.5, 333.2],
        }
    else:
        try:
            series = parse_dataset_content(payload.file_name, payload.content)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    dataset = create_dataset(
        db,
        title=payload.title,
        problem_type=payload.problem_type,
        capacity_range=payload.capacity_range,
        description=payload.description,
        source=payload.source,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        series=series,
    )
    return serialize_dataset(dataset)


@router.patch("/datasets/{dataset_id}", response_model=BatteryExampleRead)
def update_admin_dataset(
    dataset_id: int,
    payload: AdminDatasetUpdateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    dataset = db.get(BatteryExample, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset_not_found")
    series = None
    if payload.content is not None:
        try:
            series = parse_dataset_content(payload.file_name or "dataset.json", payload.content)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    updated = update_dataset(
        db,
        dataset,
        title=payload.title,
        problem_type=payload.problem_type,
        capacity_range=payload.capacity_range,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        series=series,
    )
    return serialize_dataset(updated)


@router.delete("/datasets/{dataset_id}", response_model=DatasetDeleteResponse)
def delete_admin_dataset(
    dataset_id: int,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> DatasetDeleteResponse:
    dataset = db.get(BatteryExample, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset_not_found")
    delete_dataset(db, dataset)
    return DatasetDeleteResponse(id=dataset_id, status="deleted")


@router.post("/datasets/mysql-import", response_model=BatteryExampleRead)
def import_admin_dataset_from_mysql(
    payload: MysqlDatasetImportRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _ = db
    try:
        dataset = import_dataset_from_mysql(
            db,
            phone=payload.phone,
            start_time=payload.start_time,
            end_time=payload.end_time,
            title=payload.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return serialize_dataset(dataset)


# -------------------------- user management --------------------------


def _user_to_read(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        phone=user.phone,
        phone_masked=mask_phone(user.phone) if user.phone else None,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        usage_quota_total=user.usage_quota_total,
        usage_quota_used=user.usage_quota_used,
        created_at=user.created_at,
    )


@router.get("/users", response_model=AdminUserListResponse)
def list_admin_users(
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
    phone: str | None = Query(default=None, description="按手机号模糊过滤"),
    role: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminUserListResponse:
    stmt = select(User)
    if phone:
        stmt = stmt.where(User.phone.like(f"%{phone}%"))
    if role:
        stmt = stmt.where(User.role == role)
    total = len(list(db.scalars(stmt).all()))  # small dataset → simple count
    rows = list(db.scalars(stmt.order_by(User.id.desc()).limit(limit).offset(offset)).all())
    return AdminUserListResponse(items=[_user_to_read(u) for u in rows], total=total)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.usage_quota_total is not None:
        if payload.usage_quota_total < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quota_must_be_non_negative")
        user.usage_quota_total = payload.usage_quota_total
    db.commit()
    db.refresh(user)
    return _user_to_read(user)


# -------------------------- system prompts --------------------------


def _prompt_to_read(item: SystemPrompt) -> SystemPromptRead:
    return SystemPromptRead(
        id=item.id,
        scope=item.scope,
        title=item.title,
        content=item.content,
        is_active=item.is_active,
        sort_order=item.sort_order,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/prompts", response_model=list[SystemPromptRead])
def get_prompts(_: str = Depends(require_admin_token), db: Session = Depends(get_db)) -> list[SystemPromptRead]:
    return [_prompt_to_read(i) for i in list_system_prompts(db)]


@router.post("/prompts", response_model=SystemPromptRead)
def post_prompt(
    payload: SystemPromptCreateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> SystemPromptRead:
    item = create_system_prompt(
        db,
        scope=payload.scope,
        title=payload.title,
        content=payload.content,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    return _prompt_to_read(item)


@router.patch("/prompts/{prompt_id}", response_model=SystemPromptRead)
def patch_prompt(
    prompt_id: int,
    payload: SystemPromptUpdateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> SystemPromptRead:
    item = db.get(SystemPrompt, prompt_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prompt_not_found")
    item = update_system_prompt(db, item, **payload.model_dump(exclude_unset=True))
    return _prompt_to_read(item)


@router.delete("/prompts/{prompt_id}")
def delete_prompt(
    prompt_id: int,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(SystemPrompt, prompt_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prompt_not_found")
    delete_system_prompt(db, item)
    return {"id": prompt_id, "status": "deleted"}


# -------------------------- welcome messages --------------------------


def _welcome_to_read(item: WelcomeMessage) -> WelcomeMessageRead:
    return WelcomeMessageRead(
        id=item.id,
        title=item.title,
        content=item.content,
        sort_order=item.sort_order,
        is_active=item.is_active,
    )


@router.get("/welcome", response_model=list[WelcomeMessageRead])
def get_welcome(_: str = Depends(require_admin_token), db: Session = Depends(get_db)) -> list[WelcomeMessageRead]:
    return [_welcome_to_read(i) for i in list_welcome_messages(db)]


@router.post("/welcome", response_model=WelcomeMessageRead)
def post_welcome(
    payload: WelcomeMessageCreateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> WelcomeMessageRead:
    item = create_welcome_message(
        db,
        title=payload.title,
        content=payload.content,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    return _welcome_to_read(item)


@router.patch("/welcome/{welcome_id}", response_model=WelcomeMessageRead)
def patch_welcome(
    welcome_id: int,
    payload: WelcomeMessageUpdateRequest,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> WelcomeMessageRead:
    item = db.get(WelcomeMessage, welcome_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="welcome_not_found")
    item = update_welcome_message(db, item, **payload.model_dump(exclude_unset=True))
    return _welcome_to_read(item)


@router.delete("/welcome/{welcome_id}")
def delete_welcome(
    welcome_id: int,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(WelcomeMessage, welcome_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="welcome_not_found")
    delete_welcome_message(db, item)
    return {"id": welcome_id, "status": "deleted"}


# -------------------------- conversations --------------------------


@router.get("/conversations", response_model=AdminConversationListResponse)
def admin_list_conversations(
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
    phone: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminConversationListResponse:
    items, total = list_admin_conversations(db, phone=phone, limit=limit, offset=offset)
    return AdminConversationListResponse(
        items=[AdminConversationRead.model_validate(item) for item in items],
        total=total,
    )


@router.get("/conversations/{conversation_id}", response_model=AdminConversationDetail)
def admin_get_conversation(
    conversation_id: int,
    _: str = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> AdminConversationDetail:
    detail = get_conversation_detail(db, conversation_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation_not_found")
    return AdminConversationDetail.model_validate(detail)
