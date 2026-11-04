import json
import logging
from datetime import datetime
from typing import Optional, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..dependencies import get_db, get_current_user
from ..models.auth import User
from ..models.settings import UserSettings, SyncEventJournal
from ..models.analysis import Analysis, Notification
from ..routes.analysis import _to_summary
from ..schemas.auth import UserResponse
from ..schemas.settings import UserSettingsOut
from ..schemas.analysis import AnalysisSummaryOut, NotificationOut
from ..services.websocket_manager import ws_manager
from ..utils.auth_utils import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Real-Time Synchronization"])


@router.websocket("/api/ws")
@router.websocket("/ws")
async def websocket_sync_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Authenticated real-time bidirectional WebSocket synchronization endpoint.
    Restricted strictly to the authenticated user owning the session.
    """
    # Extract token from query parameter or authorization headers
    auth_token = token
    if not auth_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]

    if not auth_token:
        # Check subprotocols
        sec_protocol = websocket.headers.get("sec-websocket-protocol")
        if sec_protocol:
            auth_token = sec_protocol.strip()

    if not auth_token:
        logger.warning("WebSocket connection rejected: No authentication token provided.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_token(auth_token)
    if not payload or not payload.get("sub"):
        logger.warning("WebSocket connection rejected: Invalid or expired token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = payload["sub"]
    from ..main import app
    from ..dependencies import get_db

    db_override = app.dependency_overrides.get(get_db)
    if db_override:
        gen = db_override()
        db = next(gen)
    else:
        db = SessionLocal()
        gen = None

    user = None
    try:
        user = db.query(User).filter(User.email == email, User.is_active == True).first()
    finally:
        if gen:
            try:
                next(gen)
            except StopIteration:
                pass
        else:
            db.close()

    if not user:
        logger.warning(f"WebSocket connection rejected: User not found for {email}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept connection and register with connection manager
    await ws_manager.connect(user.id, websocket)

    # Dispatch welcome handshake with current server state
    welcome_payload = {
        "event": "connected",
        "user_id": user.id,
        "server_time": datetime.utcnow().isoformat() + "Z",
        "version": getattr(user, "version", 1),
    }
    await websocket.send_text(json.dumps(welcome_payload))

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                msg_type = msg.get("type") or msg.get("action")
                if msg_type == "ping":
                    pong = {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                    await websocket.send_text(json.dumps(pong))
            except Exception:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(user.id, websocket)
    except Exception as exc:
        logger.info(f"WebSocket closed with exception: {exc}")
        await ws_manager.disconnect(user.id, websocket)


@router.get("/api/sync/events", summary="Query missed sync events for offline recovery")
def get_sync_events(
    since_id: Optional[int] = Query(None, description="Fetch events with ID greater than this"),
    since_time: Optional[datetime] = Query(None, description="Fetch events created after this timestamp"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return recent synchronization events for the authenticated user to reconcile missed state.
    """
    query = db.query(SyncEventJournal).filter(SyncEventJournal.user_id == current_user.id)
    if since_id is not None:
        query = query.filter(SyncEventJournal.id > since_id)
    if since_time is not None:
        query = query.filter(SyncEventJournal.created_at > since_time)

    records = query.order_by(SyncEventJournal.id.asc()).limit(limit).all()
    events = []
    for r in records:
        try:
            payload_dict = json.loads(r.payload)
        except Exception:
            payload_dict = {"event": r.event_type, "data": {}}
        events.append({
            "id": r.id,
            "event_type": r.event_type,
            "version": r.version,
            "entity_id": r.entity_id,
            "created_at": r.created_at,
            "payload": payload_dict,
        })
    return {"events": events, "count": len(events)}


@router.get("/api/sync/state", summary="Authoritative snapshot reconciliation")
def get_authoritative_state(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return complete, authoritative single-round-trip state snapshot:
    user profile, settings, notification counters, and recent analyses.
    Used for instant reconciliation upon client reconnect.
    """
    # 1. User profile
    user_out = UserResponse.model_validate(current_user)

    # 2. Settings
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(
            user_id=current_user.id,
            sensitivity_tolerance=80.0,
            api_key=f"dg_live_2026_{current_user.id:04d}x{int(datetime.utcnow().timestamp())}",
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    settings_out = UserSettingsOut.model_validate(settings)

    # 3. Notifications count
    unread_notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()

    # 4. Recent analyses
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(50)
        .all()
    )
    total_analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).count()

    return {
        "server_time": datetime.utcnow().isoformat() + "Z",
        "user": user_out,
        "settings": settings_out,
        "unread_notifications": unread_notifs,
        "total_analyses": total_analyses,
        "recent_analyses": [_to_summary(a) for a in analyses],
    }
