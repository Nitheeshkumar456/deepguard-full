"""
analysis.py — REST API router for media upload and analysis management.

Endpoints:
    POST   /api/analysis/image        Upload an image for analysis
    POST   /api/analysis/video        Upload a video for analysis
    POST   /api/analysis/audio        Upload an audio file for analysis
    GET    /api/analysis/history      List authenticated user's analyses
    GET    /api/analysis/{id}         Get full detail of a single analysis
    DELETE /api/analysis/{id}         Delete an analysis record and its file
"""

import os
import math
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query, status, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal

from ..dependencies import get_db, get_current_user
from ..models.auth import User
from ..models.analysis import Analysis, AnalysisStatus, MediaType
from ..schemas.analysis import (
    AnalysisSubmitResponse,
    AnalysisDetailOut,
    AnalysisHistoryOut,
    AnalysisSummaryOut,
    DeleteResponse,
)
from ..services.analysis_service import (
    ingest_upload,
    get_analysis_by_id,
    get_analysis_history,
    delete_analysis,
)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


# ─────────────────────────────────────────────
# Helper: map ORM Analysis → AnalysisSummaryOut
# ─────────────────────────────────────────────

def _to_summary(a: Analysis) -> AnalysisSummaryOut:
    """Flatten analysis + result into a summary schema."""
    summary = AnalysisSummaryOut.model_validate(a)
    if a.result:
        summary.prediction = a.result.prediction
        summary.confidence = a.result.confidence
        summary.risk_level = a.result.risk_level
    return summary


# ─────────────────────────────────────────────
# Upload endpoints
# ─────────────────────────────────────────────

@router.post(
    "/image",
    response_model=AnalysisSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload image for analysis",
)
async def upload_image(
    file: UploadFile = File(..., description="Image file to analyse"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept an image upload, validate it, and queue it for deepfake analysis.
    Returns the new analysis record ID and its initial processing status.
    """
    analysis = await ingest_upload(
        file=file,
        declared_media_type="image",
        current_user=current_user,
        db=db,
    )
    return AnalysisSubmitResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        message="Image received and queued for analysis.",
        media_type=analysis.media_type,
        original_filename=analysis.original_filename,
        file_size=analysis.file_size,
    )


@router.post(
    "/video",
    response_model=AnalysisSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload video for analysis",
)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file to analyse"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept a video upload, validate it, and queue it for deepfake analysis.
    Returns the new analysis record ID and its initial processing status.
    """
    analysis = await ingest_upload(
        file=file,
        declared_media_type="video",
        current_user=current_user,
        db=db,
        background_tasks=background_tasks,
    )
    return AnalysisSubmitResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        message="Video received and queued for analysis.",
        media_type=analysis.media_type,
        original_filename=analysis.original_filename,
        file_size=analysis.file_size,
    )


@router.post(
    "/audio",
    response_model=AnalysisSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload audio for analysis",
)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to analyse"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept an audio upload, validate it, and queue it for deepfake analysis.
    Returns the new analysis record ID and its initial processing status.
    """
    analysis = await ingest_upload(
        file=file,
        declared_media_type="audio",
        current_user=current_user,
        db=db,
        background_tasks=background_tasks,
    )
    return AnalysisSubmitResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        message="Audio received and queued for analysis.",
        media_type=analysis.media_type,
        original_filename=analysis.original_filename,
        file_size=analysis.file_size,
    )


# ─────────────────────────────────────────────
# History / list endpoint
# ─────────────────────────────────────────────

@router.get(
    "/history",
    response_model=AnalysisHistoryOut,
    summary="Get analysis history",
)
def get_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    media_type: Optional[str] = Query(None, description="Filter by media type: image | video | audio"),
    analysis_status: Optional[str] = Query(None, alias="status", description="Filter by status: queued | processing | completed | failed"),
    prediction: Optional[str] = Query(None, description="Filter by prediction verdict: authentic | synthetic | uncertain"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of the authenticated user's analyses.
    Supports optional filtering by media type, status, and prediction verdict.
    """
    items, total = get_analysis_history(
        current_user=current_user,
        db=db,
        page=page,
        page_size=page_size,
        media_type=media_type,
        analysis_status=analysis_status,
        prediction=prediction,
    )
    pages = max(1, math.ceil(total / page_size))
    return AnalysisHistoryOut(
        items=[_to_summary(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ─────────────────────────────────────────────
# Single analysis detail endpoint
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Single analysis detail endpoint
# ─────────────────────────────────────────────

@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailOut,
    summary="Get analysis detail",
)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return full detail for a single analysis record including result,
    forensic indicators, and explainability heatmap metadata.
    Access is restricted to the owning user.
    """
    analysis = get_analysis_by_id(analysis_id, current_user, db)
    out = AnalysisDetailOut.model_validate(analysis)
    
    # Enrich with heatmap availability
    if analysis.status == AnalysisStatus.completed:
        if analysis.media_type == MediaType.image:
            out.heatmap_available = True
            out.heatmap_url = f"/api/analysis/{analysis.id}/heatmap"
            out.original_media_url = f"/api/analysis/{analysis.id}/media"
        elif analysis.media_type == MediaType.video:
            out.heatmap_available = True
            out.heatmap_url = f"/api/analysis/{analysis.id}/heatmap?frame=0"
            out.original_media_url = f"/api/analysis/{analysis.id}/media"
        else:
            out.heatmap_available = False
    else:
        out.heatmap_available = False
        
    return out


# ─────────────────────────────────────────────
# Explainable AI Heatmap endpoints
# ─────────────────────────────────────────────

def _resolve_storage_file(analysis: Analysis) -> Optional[str]:
    """Robustly resolve absolute path to the stored media file."""
    if not analysis.storage_path:
        return None
    if os.path.isabs(analysis.storage_path) and os.path.isfile(analysis.storage_path):
        return analysis.storage_path

    # Try relative to backend/uploads
    upload_base = Path(__file__).parents[2] / "uploads"
    cand1 = upload_base / analysis.storage_path
    if cand1.is_file():
        return str(cand1.resolve())

    # Try relative to cwd
    cand2 = Path(analysis.storage_path)
    if cand2.is_file():
        return str(cand2.resolve())

    return None


@router.get(
    "/{analysis_id}/heatmap",
    summary="Get Grad-CAM explainability heatmap",
)
def get_analysis_heatmap(
    analysis_id: int,
    frame: Optional[int] = Query(None, description="Keyframe index for video heatmaps (e.g. 0, 1, 2, ...)"),
    type: str = Query("overlay", description="Visualization type: 'overlay' (blend) or 'heatmap' (pure CAM)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the Grad-CAM explainability heatmap visualization image.
    Generates and caches on first access. Requires authenticated owner.
    """
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    from ..services.gradcam_service import (
        HEATMAP_CACHE_DIR,
        generate_image_gradcam,
        generate_video_gradcam_frames,
    )

    analysis = get_analysis_by_id(analysis_id, current_user, db)

    if analysis.status != AnalysisStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heatmap is only available for completed analyses.",
        )

    abs_storage_path = _resolve_storage_file(analysis)
    if not abs_storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original media file not found for heatmap generation.",
        )

    if analysis.media_type == MediaType.image:
        overlay_file = HEATMAP_CACHE_DIR / f"{analysis.id}_gradcam.jpg"
        heatmap_file = HEATMAP_CACHE_DIR / f"{analysis.id}_heatmap.jpg"

        if not overlay_file.is_file() or not heatmap_file.is_file():
            try:
                generate_image_gradcam(
                    image_path=abs_storage_path,
                    overlay_out_path=str(overlay_file),
                    heatmap_out_path=str(heatmap_file),
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate Grad-CAM heatmap: {exc}",
                )

        target_file = heatmap_file if type == "heatmap" else overlay_file
        return FileResponse(
            str(target_file),
            media_type="image/jpeg",
            filename=f"deepguard_gradcam_{analysis.id}.jpg",
        )

    elif analysis.media_type == MediaType.video:
        frame_idx = frame if frame is not None else 0
        overlay_file = HEATMAP_CACHE_DIR / f"{analysis.id}_frame_{frame_idx}_gradcam.jpg"

        if not overlay_file.is_file():
            try:
                frames_meta = generate_video_gradcam_frames(
                    video_path=abs_storage_path,
                    analysis_id=analysis.id,
                    num_frames=5,
                )
                if not frames_meta:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="No keyframes could be extracted for video heatmap.",
                    )
                # Find matching frame file or fallback to first
                matching = next((f for f in frames_meta if f["frame_index"] == frame_idx), frames_meta[0])
                overlay_file = Path(matching["heatmap_path"])
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate video Grad-CAM heatmaps: {exc}",
                )

        return FileResponse(
            str(overlay_file),
            media_type="image/jpeg",
            filename=f"deepguard_video_gradcam_{analysis.id}_f{frame_idx}.jpg",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heatmap visualization is unavailable for audio files.",
        )


@router.get(
    "/{analysis_id}/media",
    summary="Get original media or extracted video frame",
)
def get_original_media(
    analysis_id: int,
    frame: Optional[int] = Query(None, description="Frame index for video frame"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the original media file or extracted keyframe for side-by-side comparison.
    Requires authenticated owner.
    """
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    from ..services.gradcam_service import (
        HEATMAP_CACHE_DIR,
        generate_video_gradcam_frames,
    )

    analysis = get_analysis_by_id(analysis_id, current_user, db)
    abs_storage_path = _resolve_storage_file(analysis)

    if not abs_storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found on disk.",
        )

    if analysis.media_type == MediaType.video and frame is not None:
        orig_frame_file = HEATMAP_CACHE_DIR / f"{analysis.id}_frame_{frame}_orig.jpg"
        if not orig_frame_file.is_file():
            try:
                frames_meta = generate_video_gradcam_frames(
                    video_path=abs_storage_path,
                    analysis_id=analysis.id,
                    num_frames=5,
                )
                matching = next((f for f in frames_meta if f["frame_index"] == frame), frames_meta[0])
                orig_frame_file = Path(matching["original_path"])
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to extract video frame: {exc}",
                )

        return FileResponse(
            str(orig_frame_file),
            media_type="image/jpeg",
            filename=f"deepguard_frame_{analysis.id}_f{frame}.jpg",
        )

    return FileResponse(
        abs_storage_path,
        media_type=analysis.mime_type or "application/octet-stream",
        filename=analysis.original_filename,
    )


# ─────────────────────────────────────────────
# Delete endpoint
# ─────────────────────────────────────────────

@router.delete(
    "/{analysis_id}",
    response_model=DeleteResponse,
    summary="Delete analysis record",
)
def delete_analysis_record(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete an analysis record and its associated uploaded file.
    Access is restricted to the owning user.
    """
    from ..services.websocket_manager import ws_manager
    delete_analysis(analysis_id, current_user, db)
    ws_manager.publish_event(
        user_id=current_user.id,
        event="media.deleted",
        data={"analysis_id": analysis_id},
        entity_id=str(analysis_id),
    )
    ws_manager.publish_event(
        user_id=current_user.id,
        event="history.updated",
        data={"action": "delete", "analysis_id": analysis_id},
        entity_id=str(analysis_id),
    )
    return DeleteResponse(message=f"Analysis #{analysis_id} deleted successfully.")


# ─────────────────────────────────────────────
# System Router: Notifications & Subscription
# ─────────────────────────────────────────────

from typing import List
from ..models.analysis import Notification, NotificationCategory, Subscription, SubscriptionTier, SubscriptionStatus
from ..schemas.analysis import NotificationOut, SubscriptionOut

system_router = APIRouter(prefix="/api", tags=["Notifications & Subscriptions"])


@system_router.get(
    "/notifications",
    response_model=List[NotificationOut],
    summary="Get user notifications",
)
def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all notifications for the authenticated user.
    If no notifications exist, creates initial onboarding notifications.
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    if not notifications:
        # Seed initial authentic notifications for the user
        seed_notifs = [
            Notification(
                user_id=current_user.id,
                category=NotificationCategory.system,
                title="Welcome to DeepGuard AI Console",
                body=f"Account initialized for {current_user.email}. Multimodal deepfake detection pipelines are operational.",
                is_read=False,
            ),
            Notification(
                user_id=current_user.id,
                category=NotificationCategory.analysis,
                title="AI Detection Pipelines Active",
                body="Dual-branch ResNet50 and temporal artifact detectors are online and ready to inspect media.",
                is_read=False,
            ),
            Notification(
                user_id=current_user.id,
                category=NotificationCategory.billing,
                title="Sandbox Subscription Active",
                body="Your Developer Sandbox quota includes standard multimodal inspection access.",
                is_read=True,
            ),
        ]
        db.add_all(seed_notifs)
        db.commit()
        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == current_user.id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    return notifications


@system_router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark single notification as read",
)
def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark a specific notification as read and publish notification.read event.
    """
    from ..services.websocket_manager import ws_manager
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    notif.is_read = True
    db.commit()
    db.refresh(notif)

    out = NotificationOut.model_validate(notif)
    ws_manager.publish_event(
        user_id=current_user.id,
        event="notification.read",
        data={"id": notification_id, "is_read": True},
        entity_id=str(notification_id),
    )
    return out


@system_router.patch(
    "/notifications/read-all",
    response_model=DeleteResponse,
    summary="Mark all notifications as read",
)
def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark all unread notifications as read and publish notification.read event.
    """
    from ..services.websocket_manager import ws_manager
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()

    ws_manager.publish_event(
        user_id=current_user.id,
        event="notification.read",
        data={"all": True, "count": count},
    )
    return DeleteResponse(message=f"Marked {count} notifications as read.")


@system_router.delete(
    "/notifications",
    response_model=DeleteResponse,
    summary="Clear all notifications",
)
def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete all notifications belonging to the authenticated user.
    """
    from ..services.websocket_manager import ws_manager
    deleted_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()

    ws_manager.publish_event(
        user_id=current_user.id,
        event="notification.read",
        data={"cleared_all": True, "count": deleted_count},
    )
    return DeleteResponse(message=f"Cleared {deleted_count} notifications successfully.")


@system_router.delete(
    "/notifications/{notification_id}",
    response_model=DeleteResponse,
    summary="Delete single notification",
)
def delete_single_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a single notification belonging to the authenticated user.
    """
    from ..services.websocket_manager import ws_manager
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    db.delete(notif)
    db.commit()

    ws_manager.publish_event(
        user_id=current_user.id,
        event="notification.read",
        data={"deleted_id": notification_id},
        entity_id=str(notification_id),
    )
    return DeleteResponse(message="Notification deleted successfully.")


@system_router.get(
    "/subscription",
    response_model=SubscriptionOut,
    summary="Get user subscription & quota",
)
def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return active subscription tier, status, and calculated quota consumption.
    """
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    tier_val = sub.tier.value if sub else "free"
    status_val = sub.status.value if sub else "active"

    # Count real completed analyses
    used_count = db.query(Analysis).filter(Analysis.user_id == current_user.id).count()
    total_quota = 10 if tier_val == "free" else 500

    return SubscriptionOut(
        tier=tier_val,
        status=status_val,
        used_analyses=used_count,
        total_analyses=total_quota,
    )

