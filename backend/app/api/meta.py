from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin_content import SystemPromptRead, WelcomeMessageRead
from app.services.admin_content_service import (
    get_active_system_prompt,
    list_welcome_messages,
)

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/welcome", response_model=list[WelcomeMessageRead])
def public_welcome(db: Session = Depends(get_db)) -> list[WelcomeMessageRead]:
    return [
        WelcomeMessageRead(
            id=item.id,
            title=item.title,
            content=item.content,
            sort_order=item.sort_order,
            is_active=item.is_active,
        )
        for item in list_welcome_messages(db, only_active=True)
    ]


@router.get("/system-prompt", response_model=SystemPromptRead | None)
def public_system_prompt(db: Session = Depends(get_db), scope: str = "default") -> SystemPromptRead | None:
    item = get_active_system_prompt(db, scope=scope)
    if item is None:
        return None
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
