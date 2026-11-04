"""
analysis_service.py — Business logic for file ingestion and analysis lifecycle.

Handles:
- Reading and validating uploaded files
- Persisting Analysis records
- Saving files to the secure upload directory
- Running AI inference for image uploads (synchronous)
- Writing AnalysisResult and AnalysisIndicator records
- Fetching analysis records with pagination
- Deleting analysis records and their associated files
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from ..config import settings
from ..models.auth import User
from ..models.analysis import (
    Analysis, AnalysisResult, AnalysisIndicator,
    AnalysisStatus, MediaType, Prediction, RiskLevel, IndicatorSeverity,
)
from ..utils.upload_validator import validate_upload
from .exceptions import AIServiceError

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Upload directory — resolved relative to this file so it is always inside
# the backend folder regardless of the working directory.
# Never exposed directly to the client.
# ─────────────────────────────────────────────────────────────────────────────

UPLOAD_DIR = getattr(settings, "UPLOAD_STORAGE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _upload_subdir(media_type: str) -> str:
    """Return (and create) the upload subdirectory for a media type."""
    path = os.path.join(UPLOAD_DIR, media_type)
    os.makedirs(path, exist_ok=True)
    return path


from fastapi import UploadFile, HTTPException, status, BackgroundTasks

async def ingest_upload(
    file: UploadFile,
    declared_media_type: str,
    current_user: User,
    db: Session,
    background_tasks: Optional[BackgroundTasks] = None,
    db_session_maker = None,
) -> Analysis:
    """
    Read, validate, store, and register an uploaded media file.

    For image uploads, runs AI inference synchronously and returns
    a completed Analysis with results. For video/audio, returns a
    queued Analysis and schedules a background task.

    Returns an Analysis record.
    Raises HTTPException on any validation or IO failure.
    """
    # ── 1. Read entire file into memory for validation ───────────────────────
    try:
        file_bytes = await file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file content.",
        )

    original_filename = file.filename or "unknown"

    # ── 2. Validate extension, size, and magic-byte MIME ────────────────────
    try:
        safe_filename, detected_mime, file_size = validate_upload(
            filename=original_filename,
            file_bytes=file_bytes,
            declared_media_type=declared_media_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # ── 3. Write to secure upload directory ─────────────────────────────────
    dest_dir = _upload_subdir(declared_media_type)
    dest_path = os.path.join(dest_dir, safe_filename)

    # Prevent path traversal — safe_filename is UUID-generated so this is
    # defensive-in-depth.
    if not os.path.abspath(dest_path).startswith(os.path.abspath(dest_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload destination path.",
        )

    try:
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage write failure. Please try again.",
        )

    # ── 4. Create Analysis record ────────────────────────────────────────────
    # Store only the relative path (media_type/safe_filename) — never expose
    # absolute server filesystem paths to the client.
    relative_path = f"{declared_media_type}/{safe_filename}"

    analysis = Analysis(
        user_id=current_user.id,
        media_type=MediaType(declared_media_type),
        original_filename=original_filename,
        file_size=file_size,
        mime_type=detected_mime,
        storage_path=relative_path,
        status=AnalysisStatus.queued,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Publish media upload and analysis start events to user's connected sessions
    from .websocket_manager import ws_manager
    from ..schemas.analysis import AnalysisSummaryOut
    summary_data = AnalysisSummaryOut.model_validate(analysis).model_dump()
    ws_manager.publish_event(
        user_id=current_user.id,
        event="media.uploaded",
        data=summary_data,
        entity_id=str(analysis.id),
    )
    ws_manager.publish_event(
        user_id=current_user.id,
        event="analysis.started",
        data=summary_data,
        entity_id=str(analysis.id),
    )
    ws_manager.publish_event(
        user_id=current_user.id,
        event="history.updated",
        data={"action": "create", "analysis_id": analysis.id, "media_type": declared_media_type},
        entity_id=str(analysis.id),
    )

    # ── 5. Run AI inference ──────────────────────────────────────────────────
    if declared_media_type == "image":
        analysis = _run_image_analysis(analysis, dest_path, db)
    elif declared_media_type in ("video", "audio") and background_tasks:
        from sqlalchemy.orm import sessionmaker
        factory = db_session_maker or sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
        background_tasks.add_task(
            _run_async_analysis_task,
            analysis.id,
            declared_media_type,
            dest_path,
            factory,
        )
    elif declared_media_type == "audio" and not background_tasks:
        analysis = _run_audio_analysis(analysis, dest_path, db)

    return analysis



def _notify_and_publish_completion(analysis: Analysis, result, db: Session):
    from ..models.analysis import Notification, NotificationCategory
    from .websocket_manager import ws_manager
    from ..schemas.analysis import AnalysisDetailOut, NotificationOut

    prediction_val = result.prediction.value if hasattr(result.prediction, "value") else str(result.prediction)
    risk_val = result.risk_level.value if hasattr(result.risk_level, "value") else str(result.risk_level)
    notif = Notification(
        user_id=analysis.user_id,
        category=NotificationCategory.analysis,
        title=f"Analysis Complete: {analysis.original_filename}",
        body=f"Authenticity verdict: {prediction_val.upper()} ({(result.confidence * 100):.1f}% confidence, {risk_val.upper()} risk).",
        is_read=False,
        related_analysis_id=analysis.id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    detail_data = AnalysisDetailOut.model_validate(analysis).model_dump()
    ws_manager.publish_event(
        user_id=analysis.user_id,
        event="analysis.completed",
        data=detail_data,
        entity_id=str(analysis.id),
    )
    ws_manager.publish_event(
        user_id=analysis.user_id,
        event="history.updated",
        data={"action": "update", "analysis_id": analysis.id, "status": "completed"},
        entity_id=str(analysis.id),
    )
    ws_manager.publish_event(
        user_id=analysis.user_id,
        event="notification.created",
        data=NotificationOut.model_validate(notif).model_dump(),
        entity_id=str(notif.id),
    )


def _notify_and_publish_failure(analysis: Analysis, error_message: str, db: Session):
    from ..models.analysis import Notification, NotificationCategory
    from .websocket_manager import ws_manager
    from ..schemas.analysis import NotificationOut

    notif = Notification(
        user_id=analysis.user_id,
        category=NotificationCategory.analysis,
        title=f"Analysis Failed: {analysis.original_filename}",
        body=f"Failed to analyse file: {error_message}",
        is_read=False,
        related_analysis_id=analysis.id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    ws_manager.publish_event(
        user_id=analysis.user_id,
        event="analysis.failed",
        data={"analysis_id": analysis.id, "error": error_message, "status": "failed"},
        entity_id=str(analysis.id),
    )
    ws_manager.publish_event(
        user_id=analysis.user_id,
        event="history.updated",
        data={"action": "update", "analysis_id": analysis.id, "status": "failed"},
        entity_id=str(analysis.id),
    )
    ws_manager.publish_event(
        user_id=analysis.user_id,
        event="notification.created",
        data=NotificationOut.model_validate(notif).model_dump(),
        entity_id=str(notif.id),
    )


def _run_image_analysis(
    analysis: Analysis,
    file_path: str,
    db: Session,
) -> Analysis:
    """
    Execute the full image analysis pipeline:
      preprocess → inference → result aggregation → risk classification → DB

    Updates the Analysis record in-place and returns it.
    On ANY failure, sets status=failed with an error message — never creates
    fake results or random confidence values.
    """
    from .ai_service import run_image_inference

    # Mark as processing
    analysis.status = AnalysisStatus.processing
    db.commit()

    try:
        # ── Run inference ───────────────────────────────────────────────────
        result = run_image_inference(file_path)

        # ── Update image dimensions from preprocessing ──────────────────────
        # (The preprocessor extracts original dimensions before resizing)
        from .image_preprocessor import load_and_validate_image
        try:
            img = load_and_validate_image(file_path)
            analysis.width = img.width
            analysis.height = img.height
            img.close()
        except Exception:
            pass  # Non-critical — don't fail analysis over metadata

        # ── Create AnalysisResult record ────────────────────────────────────
        analysis_result = AnalysisResult(
            analysis_id=analysis.id,
            prediction=Prediction(result.prediction),
            confidence=result.confidence,
            risk_level=RiskLevel(result.risk_level),
            model_name=result.model_name,
            model_version=result.model_version,
            face_manipulation_score=result.face_manipulation_score,
            gan_artifact_score=result.gan_artifact_score,
            spectral_anomaly_score=result.spectral_anomaly_score,
        )
        db.add(analysis_result)

        # ── Create AnalysisIndicator records ────────────────────────────────
        for ind in result.indicators:
            indicator = AnalysisIndicator(
                analysis_id=analysis.id,
                indicator_type=ind.indicator_type,
                description=ind.description,
                severity=IndicatorSeverity(ind.severity),
                region_x=ind.region_x,
                region_y=ind.region_y,
                region_w=ind.region_w,
                region_h=ind.region_h,
            )
            db.add(indicator)

        # ── Mark analysis as completed ──────────────────────────────────────
        analysis.status = AnalysisStatus.completed
        analysis.processing_time = result.processing_time_seconds
        analysis.completed_at = datetime.utcnow()
        analysis.error_message = None

        db.commit()
        db.refresh(analysis)

        logger.info(
            "Image analysis completed: analysis_id=%d, prediction=%s, "
            "confidence=%.4f, risk=%s, time=%.3fs",
            analysis.id, result.prediction, result.confidence,
            result.risk_level, result.processing_time_seconds,
        )

        _notify_and_publish_completion(analysis, result, db)

    except AIServiceError as exc:
        # Known AI service error — set failed status with specific message
        analysis.status = AnalysisStatus.failed
        analysis.error_message = str(exc.message)
        analysis.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)

        logger.error(
            "Image analysis failed: analysis_id=%d, error=%s",
            analysis.id, exc.message,
        )
        _notify_and_publish_failure(analysis, str(exc.message), db)

    except Exception as exc:
        # Unexpected error — set failed status with generic message
        err_msg = f"Unexpected analysis error: {type(exc).__name__}: {exc}"
        analysis.status = AnalysisStatus.failed
        analysis.error_message = err_msg
        analysis.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)

        logger.exception(
            "Unexpected error during image analysis: analysis_id=%d",
            analysis.id,
        )
        _notify_and_publish_failure(analysis, err_msg, db)

    return analysis


def _run_audio_analysis(
    analysis: Analysis,
    file_path: str,
    db: Session,
) -> Analysis:
    """
    Execute the audio deepfake analysis pipeline synchronously:
      decode & preprocess → AASIST inference → result aggregation → DB commit
    """
    from .ai_service import run_audio_inference
    from .audio_preprocessor import load_audio_file

    analysis.status = AnalysisStatus.processing
    db.commit()

    try:
        try:
            data, sr, ch = load_audio_file(file_path)
            analysis.duration_seconds = round(len(data) / float(sr), 2)
        except Exception:
            pass

        result = run_audio_inference(file_path)

        # Clean any stale records
        existing_result = db.query(AnalysisResult).filter(AnalysisResult.analysis_id == analysis.id).first()
        if existing_result:
            db.delete(existing_result)
        db.query(AnalysisIndicator).filter(AnalysisIndicator.analysis_id == analysis.id).delete()
        db.commit()

        analysis_result = AnalysisResult(
            analysis_id=analysis.id,
            prediction=Prediction(result.prediction),
            confidence=result.confidence,
            risk_level=RiskLevel(result.risk_level),
            model_name=result.model_name,
            model_version=result.model_version,
            voice_cloning_score=result.voice_cloning_score,
            spectral_anomaly_score=result.spectral_anomaly_score,
        )
        db.add(analysis_result)

        for ind in result.indicators:
            indicator = AnalysisIndicator(
                analysis_id=analysis.id,
                indicator_type=ind.indicator_type,
                description=ind.description,
                severity=IndicatorSeverity(ind.severity),
                region_x=ind.region_x,
                region_y=ind.region_y,
                region_w=ind.region_w,
                region_h=ind.region_h,
            )
            db.add(indicator)

        analysis.status = AnalysisStatus.completed
        analysis.processing_time = result.processing_time_seconds
        analysis.completed_at = datetime.utcnow()
        analysis.error_message = None

        db.commit()
        db.refresh(analysis)

        logger.info(
            "Audio analysis completed: analysis_id=%d, prediction=%s, confidence=%.4f, risk=%s",
            analysis.id, result.prediction, result.confidence, result.risk_level
        )
        _notify_and_publish_completion(analysis, result, db)

    except AIServiceError as exc:
        analysis.status = AnalysisStatus.failed
        analysis.error_message = str(exc.message)
        analysis.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)
        logger.error("Audio analysis failed: analysis_id=%d, error=%s", analysis.id, exc.message)
        _notify_and_publish_failure(analysis, str(exc.message), db)

    except Exception as exc:
        err_msg = f"Unexpected audio analysis error: {type(exc).__name__}: {exc}"
        analysis.status = AnalysisStatus.failed
        analysis.error_message = err_msg
        analysis.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)
        logger.exception("Unexpected error during audio analysis: analysis_id=%d", analysis.id)
        _notify_and_publish_failure(analysis, err_msg, db)

    return analysis


def _run_async_analysis_task(
    analysis_id: int,
    media_type: str,
    file_path: str,
    db_session_maker,
):
    """
    Background task to run video or audio inference.
    """
    db = db_session_maker()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            logger.error(f"Analysis task failed: record {analysis_id} not found.")
            return

        # Mark as processing
        analysis.status = AnalysisStatus.processing
        db.commit()

        from .ai_service import run_video_inference, run_audio_inference
        
        try:
            if media_type == "video":
                result = run_video_inference(file_path)
            elif media_type == "audio":
                try:
                    from .audio_preprocessor import load_audio_file
                    data, sr, ch = load_audio_file(file_path)
                    analysis.duration_seconds = round(len(data) / float(sr), 2)
                except Exception:
                    pass
                result = run_audio_inference(file_path)
            else:
                raise AIServiceError(f"Unsupported async media type: {media_type}")

            # Clean any stale result or indicators for this analysis_id
            existing_result = db.query(AnalysisResult).filter(AnalysisResult.analysis_id == analysis.id).first()
            if existing_result:
                db.delete(existing_result)
            db.query(AnalysisIndicator).filter(AnalysisIndicator.analysis_id == analysis.id).delete()
            db.commit()

            # Create AnalysisResult record
            analysis_result = AnalysisResult(
                analysis_id=analysis.id,
                prediction=Prediction(result.prediction),
                confidence=result.confidence,
                risk_level=RiskLevel(result.risk_level),
                model_name=result.model_name,
                model_version=result.model_version,
                face_manipulation_score=result.face_manipulation_score,
                gan_artifact_score=result.gan_artifact_score,
                temporal_inconsistency_score=result.temporal_inconsistency_score,
                voice_cloning_score=result.voice_cloning_score,
                spectral_anomaly_score=result.spectral_anomaly_score,
            )
            db.add(analysis_result)

            # Create AnalysisIndicator records
            for ind in result.indicators:
                indicator = AnalysisIndicator(
                    analysis_id=analysis.id,
                    indicator_type=ind.indicator_type,
                    description=ind.description,
                    severity=IndicatorSeverity(ind.severity),
                    region_x=ind.region_x,
                    region_y=ind.region_y,
                    region_w=ind.region_w,
                    region_h=ind.region_h,
                )
                db.add(indicator)

            # Mark analysis as completed
            analysis.status = AnalysisStatus.completed
            analysis.processing_time = result.processing_time_seconds
            analysis.completed_at = datetime.utcnow()
            analysis.error_message = None
            db.commit()
            db.refresh(analysis)

            logger.info(
                f"Async {media_type} analysis completed: analysis_id={analysis.id}, "
                f"prediction={result.prediction}, confidence={result.confidence:.4f}"
            )
            _notify_and_publish_completion(analysis, result, db)

        except AIServiceError as exc:
            db.rollback()
            try:
                analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
                if analysis:
                    analysis.status = AnalysisStatus.failed
                    analysis.error_message = str(exc.message)
                    analysis.completed_at = datetime.utcnow()
                    db.commit()
                    db.refresh(analysis)
                    _notify_and_publish_failure(analysis, str(exc.message), db)
            except Exception:
                pass
            logger.error(f"Async {media_type} analysis failed: analysis_id={analysis_id}, error={exc.message}")

        except Exception as exc:
            db.rollback()
            try:
                analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
                if analysis:
                    err_msg = f"Unexpected analysis error: {type(exc).__name__}: {exc}"
                    analysis.status = AnalysisStatus.failed
                    analysis.error_message = err_msg
                    analysis.completed_at = datetime.utcnow()
                    db.commit()
                    db.refresh(analysis)
                    _notify_and_publish_failure(analysis, err_msg, db)
            except Exception:
                pass
            logger.exception(f"Unexpected error during async {media_type} analysis: analysis_id={analysis_id}")

    finally:
        db.close()


def get_analysis_by_id(
    analysis_id: int,
    current_user: User,
    db: Session,
) -> Analysis:
    """
    Fetch a single Analysis owned by current_user, raising 404 if not found
    or 403 if the record belongs to another user.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis record #{analysis_id} not found.",
        )
    if analysis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this analysis record.",
        )
    return analysis


def get_analysis_history(
    current_user: User,
    db: Session,
    page: int = 1,
    page_size: int = 20,
    media_type: Optional[str] = None,
    analysis_status: Optional[str] = None,
    prediction: Optional[str] = None,
) -> Tuple[list, int]:
    """
    Return paginated analysis history for the current user with optional filters.
    Returns (items, total_count).
    """
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)

    if media_type:
        try:
            query = query.filter(Analysis.media_type == MediaType(media_type))
        except ValueError:
            pass  # invalid filter value — ignore silently

    if analysis_status:
        try:
            query = query.filter(Analysis.status == AnalysisStatus(analysis_status))
        except ValueError:
            pass

    if prediction:
        from ..models.analysis import AnalysisResult, Prediction
        try:
            pred_enum = Prediction(prediction)
            query = query.join(AnalysisResult).filter(AnalysisResult.prediction == pred_enum)
        except ValueError:
            pass

    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def delete_analysis(
    analysis_id: int,
    current_user: User,
    db: Session,
) -> None:
    """
    Delete an Analysis record and its associated uploaded file.
    Raises appropriate HTTP errors if not found or access denied.
    """
    analysis = get_analysis_by_id(analysis_id, current_user, db)

    # Remove file from disk if it exists
    if analysis.storage_path:
        abs_path = os.path.join(UPLOAD_DIR, analysis.storage_path)
        # Prevent traversal once more
        if os.path.abspath(abs_path).startswith(os.path.abspath(UPLOAD_DIR)):
            try:
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except OSError:
                pass  # Best-effort cleanup — don't block DB deletion

    db.delete(analysis)
    db.commit()
