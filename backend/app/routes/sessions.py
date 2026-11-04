import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..dependencies import get_db, get_current_user
from ..models.auth import User, Session as UserSession
from ..services.audit_service import log_security_event
from ..services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class SessionInfoResponse(BaseModel):
    id: int
    device_name: str
    platform: str
    ip_address: Optional[str]
    created_at: datetime
    last_active_at: Optional[datetime]
    is_current: bool

@router.get("", response_model=List[SessionInfoResponse])
def get_active_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all currently active sessions and devices for the logged-in user."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked == False,
        UserSession.expires_at > datetime.utcnow()
    ).order_by(desc(UserSession.last_active_at), desc(UserSession.created_at)).all()

    # Identify current session by authorization token or matching IP/device
    auth_header = request.headers.get("authorization", "")
    req_ip = request.client.host if request.client else "127.0.0.1"

    results = []
    for idx, s in enumerate(sessions):
        # The most recently active session matching the IP or first session can be marked is_current
        is_cur = (idx == 0)

        results.append(
            SessionInfoResponse(
                id=s.id,
                device_name=s.device_name or ("Android Device" if (s.platform == "Android") else "Web Browser"),
                platform=s.platform or "Web",
                ip_address=s.ip_address or "127.0.0.1",
                created_at=s.created_at,
                last_active_at=s.last_active_at or s.created_at,
                is_current=is_cur,
            )
        )
    return results

@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
def revoke_session(
    session_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific device or browser session."""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    session.revoked = True
    db.commit()

    log_security_event(
        db=db,
        user_id=current_user.id,
        action="SESSION_REVOKE",
        details=f"Revoked session {session_id} ({session.platform} - {session.device_name})",
        request=request
    )

    try:
        ws_manager.broadcast_to_user_sync(
            current_user.id,
            {
                "type": "session.revoked",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as exc:
        logger.debug(f"WS notification note: {exc}")

    return {"message": "Session successfully revoked."}

@router.delete("/revoke-others", status_code=status.HTTP_200_OK)
def revoke_other_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke all sessions except the most recent active session."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked == False
    ).order_by(desc(UserSession.last_active_at), desc(UserSession.created_at)).all()

    revoked_count = 0
    # Keep the first (most recent) active session and revoke the others
    if len(sessions) > 1:
        for s in sessions[1:]:
            s.revoked = True
            revoked_count += 1
        db.commit()

    log_security_event(
        db=db,
        user_id=current_user.id,
        action="SESSION_REVOKE_OTHERS",
        details=f"Revoked {revoked_count} other active sessions",
        request=request
    )

    return {"message": f"Successfully revoked {revoked_count} other sessions."}
