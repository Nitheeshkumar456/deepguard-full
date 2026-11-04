from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_current_user
from ..models.auth import User
from ..models.settings import UserSettings
from ..schemas.settings import UserSettingsOut, UserSettingsUpdate
from ..services.websocket_manager import ws_manager

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _get_or_create_settings(user_id: int, db: Session) -> UserSettings:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not settings:
        settings = UserSettings(
            user_id=user_id,
            sensitivity_tolerance=80.0,
            api_key=f"dg_live_2026_{user_id:04d}x{int(datetime.utcnow().timestamp())}",
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=UserSettingsOut, summary="Get user account settings")
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve authoritative account-level settings including sensitivity tolerance and API key.
    """
    settings = _get_or_create_settings(current_user.id, db)
    return settings


@router.put("", response_model=UserSettingsOut, summary="Update account settings")
def update_settings(
    update_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update account settings with optimistic concurrency control.
    Publishes 'settings.updated' event upon successful transaction.
    """
    settings = _get_or_create_settings(current_user.id, db)

    # Concurrency check
    if update_data.version is not None and update_data.version != settings.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Conflict: Settings have been modified on another client device.",
                "current_version": settings.version,
                "current_settings": {
                    "sensitivity_tolerance": settings.sensitivity_tolerance,
                    "api_key": settings.api_key,
                    "version": settings.version,
                    "updated_at": settings.updated_at.isoformat(),
                },
            },
        )

    if update_data.sensitivity_tolerance is not None:
        settings.sensitivity_tolerance = max(0.0, min(100.0, float(update_data.sensitivity_tolerance)))

    if update_data.api_key is not None:
        settings.api_key = update_data.api_key.strip()

    settings.version += 1
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)

    # Publish real-time event to all connected sessions for this user
    out = UserSettingsOut.model_validate(settings)
    ws_manager.publish_event(
        user_id=current_user.id,
        event="settings.updated",
        data=out.model_dump(),
        version=settings.version,
        entity_id=str(settings.id),
    )

    return out
