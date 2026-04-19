from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import generate_access_token, generate_invite_code
from app.models.demo_session import DemoSession
from app.models.invite import InviteCode, InviteRedemption
from app.models.user import User

PUBLIC_DEMO_INVITE_CODE = "PUBLIC-DEMO-001"


def list_invites(db: Session) -> list[InviteCode]:
    return list(db.scalars(select(InviteCode).order_by(InviteCode.id.desc())).all())


def seed_public_demo_invite(db: Session, settings: Settings) -> InviteCode:
    existing = db.scalar(select(InviteCode).where(InviteCode.code == PUBLIC_DEMO_INVITE_CODE))
    if existing:
        return existing
    return create_invite(
        db,
        settings,
        name="公开演示体验码",
        code=PUBLIC_DEMO_INVITE_CODE,
        max_uses=max(settings.invite_default_max_uses, 50),
        per_user_quota=max(settings.invite_default_per_user_quota, 10),
    )


def create_invite(
    db: Session,
    settings: Settings,
    *,
    name: str,
    code: str | None = None,
    max_uses: int | None = None,
    per_user_quota: int | None = None,
    expires_at: datetime | None = None,
    created_by_user_id: int | None = None,
) -> InviteCode:
    invite = InviteCode(
        code=code or generate_invite_code(),
        name=name,
        max_uses=max_uses or settings.invite_default_max_uses,
        per_user_quota=per_user_quota or settings.invite_default_per_user_quota,
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
        is_active=True,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def update_invite(db: Session, invite: InviteCode, **changes: object) -> InviteCode:
    for field_name, value in changes.items():
        if value is not None and hasattr(invite, field_name):
            setattr(invite, field_name, value)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def _is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        return expires_at <= datetime.utcnow()
    return expires_at <= datetime.now(expires_at.tzinfo)


def start_demo_session(db: Session, settings: Settings, invite_code_value: str) -> tuple[InviteCode, User, DemoSession]:
    invite = db.scalar(select(InviteCode).where(InviteCode.code == invite_code_value))
    if not invite:
        raise ValueError("invite_not_found")
    if not invite.is_active:
        raise ValueError("invite_disabled")
    if invite.used_uses >= invite.max_uses:
        raise ValueError("invite_exhausted")
    if _is_expired(invite.expires_at):
        raise ValueError("invite_expired")

    invite.used_uses += 1
    user = User(
        username=f"guest_{invite.code.replace('-', '').lower()}_{invite.used_uses}",
        role="user",
        invite_code_id=invite.id,
        usage_quota_total=invite.per_user_quota,
        usage_quota_used=0,
        is_active=True,
    )
    db.add(user)
    db.flush()

    session = DemoSession(
        session_token=generate_access_token(prefix="demo"),
        user_id=user.id,
        invite_code_id=invite.id,
        is_active=True,
    )
    db.add(session)
    redemption = InviteRedemption(invite_code_id=invite.id, user_id=user.id)
    db.add(redemption)
    db.commit()
    db.refresh(invite)
    db.refresh(user)
    db.refresh(session)
    return invite, user, session


def get_demo_session_by_token(db: Session, session_token: str) -> DemoSession | None:
    return db.scalar(select(DemoSession).where(DemoSession.session_token == session_token))
