"""Mock SMS verification flow.

We never actually deliver an SMS. The flow is:

1. ``/auth/sms/send`` records a row in ``sms_codes`` with a 5-minute TTL,
   subject to a 60-second per-phone rate limit. The generated code is logged
   for developer convenience and returned to the client (mock-mode only).
2. ``/auth/sms/login`` looks up an unconsumed, unexpired row for the phone.
   The user-submitted code is intentionally NOT compared against the stored
   one — per requirements "默认都正确" — but the row must exist.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sms_code import SmsCode

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=5)
RESEND_COOLDOWN = timedelta(seconds=60)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def issue_sms_code(db: Session, phone: str) -> SmsCode:
    """Create a new SMS code (or reuse a recent one within the cooldown window)."""
    if not phone:
        raise ValueError("phone_required")

    cutoff = _now() - RESEND_COOLDOWN
    recent = db.scalar(
        select(SmsCode)
        .where(SmsCode.phone == phone, SmsCode.created_at >= cutoff, SmsCode.consumed.is_(False))
        .order_by(SmsCode.created_at.desc())
    )
    if recent is not None:
        return recent

    code = f"{secrets.randbelow(1_000_000):06d}"
    record = SmsCode(phone=phone, code=code, expires_at=_now() + CODE_TTL)
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("sms.mock_send phone=%s code=%s", phone[-4:], code)
    return record


def consume_sms_code(db: Session, phone: str) -> bool:
    """Return True if a valid unconsumed code exists for the phone, marking it consumed.

    The submitted user code is intentionally not verified against the stored
    value (mock environment).
    """
    record = db.scalar(
        select(SmsCode)
        .where(
            SmsCode.phone == phone,
            SmsCode.consumed.is_(False),
            SmsCode.expires_at > _now(),
        )
        .order_by(SmsCode.created_at.desc())
    )
    if record is None:
        return False
    record.consumed = True
    db.add(record)
    db.commit()
    return True
