from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_content import SystemPrompt, WelcomeMessage


# -------- system prompts --------


def list_system_prompts(db: Session, *, only_active: bool = False) -> list[SystemPrompt]:
    stmt = select(SystemPrompt).order_by(SystemPrompt.sort_order.asc(), SystemPrompt.id.asc())
    if only_active:
        stmt = stmt.where(SystemPrompt.is_active.is_(True))
    return list(db.scalars(stmt).all())


def get_active_system_prompt(db: Session, scope: str = "default") -> SystemPrompt | None:
    return db.scalar(
        select(SystemPrompt)
        .where(SystemPrompt.scope == scope, SystemPrompt.is_active.is_(True))
        .order_by(SystemPrompt.sort_order.asc(), SystemPrompt.id.asc())
    )


def create_system_prompt(
    db: Session,
    *,
    scope: str,
    title: str,
    content: str,
    is_active: bool = True,
    sort_order: int = 0,
) -> SystemPrompt:
    item = SystemPrompt(scope=scope, title=title, content=content, is_active=is_active, sort_order=sort_order)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_system_prompt(
    db: Session,
    item: SystemPrompt,
    *,
    scope: str | None = None,
    title: str | None = None,
    content: str | None = None,
    is_active: bool | None = None,
    sort_order: int | None = None,
) -> SystemPrompt:
    if scope is not None:
        item.scope = scope
    if title is not None:
        item.title = title
    if content is not None:
        item.content = content
    if is_active is not None:
        item.is_active = is_active
    if sort_order is not None:
        item.sort_order = sort_order
    db.commit()
    db.refresh(item)
    return item


def delete_system_prompt(db: Session, item: SystemPrompt) -> None:
    db.delete(item)
    db.commit()


# -------- welcome messages --------


def list_welcome_messages(db: Session, *, only_active: bool = False) -> list[WelcomeMessage]:
    stmt = select(WelcomeMessage).order_by(WelcomeMessage.sort_order.asc(), WelcomeMessage.id.asc())
    if only_active:
        stmt = stmt.where(WelcomeMessage.is_active.is_(True))
    return list(db.scalars(stmt).all())


def create_welcome_message(
    db: Session,
    *,
    title: str,
    content: str,
    sort_order: int = 0,
    is_active: bool = True,
) -> WelcomeMessage:
    item = WelcomeMessage(title=title, content=content, sort_order=sort_order, is_active=is_active)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_welcome_message(
    db: Session,
    item: WelcomeMessage,
    *,
    title: str | None = None,
    content: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> WelcomeMessage:
    if title is not None:
        item.title = title
    if content is not None:
        item.content = content
    if sort_order is not None:
        item.sort_order = sort_order
    if is_active is not None:
        item.is_active = is_active
    db.commit()
    db.refresh(item)
    return item


def delete_welcome_message(db: Session, item: WelcomeMessage) -> None:
    db.delete(item)
    db.commit()
