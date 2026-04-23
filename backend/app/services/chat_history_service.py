"""Persisting chat history for replay / audit / admin inspection.

A ChatSession is created lazily on the first user message of an agent run, and
messages are appended as the turn progresses. For admin listing we expose
session-level summaries + paginated message fetches.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.demo_session import DemoSession
from app.models.user import User


def create_chat_session(
    db: Session, *, demo_session_id: int | None, title: str = "对话", battery_example_id: int | None = None
) -> ChatSession:
    item = ChatSession(demo_session_id=demo_session_id, title=title[:128], battery_example_id=battery_example_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def append_message(
    db: Session,
    session_id: int,
    *,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def list_admin_conversations(
    db: Session,
    *,
    phone: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return paginated session summaries joined with the owning user's phone."""
    base = (
        select(ChatSession, User)
        .outerjoin(DemoSession, ChatSession.demo_session_id == DemoSession.id)
        .outerjoin(User, DemoSession.user_id == User.id)
    )
    count_stmt = select(func.count()).select_from(base.subquery())
    if phone:
        base = base.where(User.phone.like(f"%{phone}%"))
        count_stmt = select(func.count()).select_from(base.subquery())
    total = db.scalar(count_stmt) or 0
    rows = db.execute(base.order_by(ChatSession.id.desc()).limit(limit).offset(offset)).all()
    items = []
    for session, user in rows:
        msg_count = db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session.id)) or 0
        items.append(
            {
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if isinstance(session.created_at, datetime) else str(session.created_at),
                "phone": user.phone if user else None,
                "phone_masked": (f"{user.phone[:3]}****{user.phone[-4:]}" if user and user.phone and len(user.phone) >= 7 else (user.phone if user else None)),
                "user_id": user.id if user else None,
                "message_count": int(msg_count),
            }
        )
    return items, int(total)


def get_conversation_detail(db: Session, session_id: int) -> dict | None:
    session = db.get(ChatSession, session_id)
    if session is None:
        return None
    msgs = list(
        db.scalars(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc())
        ).all()
    )
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if isinstance(session.created_at, datetime) else str(session.created_at),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": json.loads(m.metadata_json) if m.metadata_json else None,
                "created_at": m.created_at.isoformat() if isinstance(m.created_at, datetime) else str(m.created_at),
            }
            for m in msgs
        ],
    }
