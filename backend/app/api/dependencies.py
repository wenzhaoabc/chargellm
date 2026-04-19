from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.demo_session import DemoSession
from app.services.invite_service import get_demo_session_by_token

demo_bearer_scheme = HTTPBearer(auto_error=False)


def require_demo_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(demo_bearer_scheme),
    db: Session = Depends(get_db),
) -> DemoSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="demo_session_token_missing")
    session = get_demo_session_by_token(db, credentials.credentials)
    if session is None or not session.is_active or session.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="demo_session_invalid")
    return session
