from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    InviteStartRequest,
    InviteStartResponse,
    SmsLoginRequest,
    SmsLoginResponse,
    SmsSendRequest,
    SmsSendResponse,
)
from app.services.auth_service import authenticate_admin, authenticate_sms_user, issue_phone_access_token, send_sms_code
from app.services.invite_service import start_demo_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/invite/start", response_model=InviteStartResponse)
def invite_start(payload: InviteStartRequest, db: Session = Depends(get_db)) -> InviteStartResponse:
    settings = get_settings()
    try:
        invite, user, session = start_demo_session(db, settings, payload.invite_code)
    except ValueError as exc:
        code = str(exc)
        if code == "invite_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invite_not_found") from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from exc

    quota_remaining = max(user.usage_quota_total - user.usage_quota_used, 0)
    return InviteStartResponse(
        invite_code=invite.code,
        session_token=session.session_token,
        demo_user_id=user.id,
        quota_total=user.usage_quota_total,
        quota_used=user.usage_quota_used,
        quota_remaining=quota_remaining,
        expires_at=invite.expires_at,
    )


@router.post("/sms/send", response_model=SmsSendResponse)
def sms_send(payload: SmsSendRequest) -> SmsSendResponse:
    settings = get_settings()
    result = send_sms_code(payload.phone, settings.sms_mock_code)
    return SmsSendResponse(**result)


@router.post("/sms/login", response_model=SmsLoginResponse)
def sms_login(payload: SmsLoginRequest, db: Session = Depends(get_db)) -> SmsLoginResponse:
    settings = get_settings()
    user = authenticate_sms_user(db, payload.phone, payload.code, settings.sms_mock_code)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sms_code_invalid")
    return SmsLoginResponse(
        access_token=issue_phone_access_token(payload.phone),
        phone_masked=payload.phone[:3] + "****" + payload.phone[-4:] if len(payload.phone) >= 7 else payload.phone,
    )


@router.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, request: Request, db: Session = Depends(get_db)) -> AdminLoginResponse:
    admin = authenticate_admin(db, payload.username, payload.password)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_login_failed")
    token = request.app.state.issue_admin_token(admin.username or payload.username)
    return AdminLoginResponse(access_token=token, admin_username=payload.username)

