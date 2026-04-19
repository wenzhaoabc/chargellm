from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import generate_access_token, hash_password, mask_phone, verify_password
from app.models.user import User


def bootstrap_admin(db: Session, settings: Settings) -> User:
    existing = db.scalar(select(User).where(User.username == settings.admin_username))
    if existing:
        return existing
    admin = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def authenticate_admin(db: Session, username: str, password: str) -> User | None:
    admin = db.scalar(select(User).where(User.username == username, User.role == "admin"))
    if not admin or not admin.password_hash:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


def send_sms_code(phone: str, mock_code: str) -> dict[str, str]:
    return {"phone_masked": mask_phone(phone), "mock_code": mock_code}


def authenticate_sms_user(db: Session, phone: str, code: str, mock_code: str) -> User | None:
    if code != mock_code:
        return None
    user = db.scalar(select(User).where(User.phone == phone))
    if user:
        return user
    user = User(phone=phone, role="user", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def issue_phone_access_token(phone: str) -> str:
    return generate_access_token(prefix=f"phone_{phone[-4:]}")

