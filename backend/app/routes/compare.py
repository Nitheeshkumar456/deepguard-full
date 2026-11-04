import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..models.auth import User
from ..models.analysis import Analysis, AnalysisStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["comparison"])

@router.get("/compare")
def compare_analyses(
    id1: int = Query(..., description="ID of the first analysis record"),
    id2: int = Query(..., description="ID of the second analysis record"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform a comprehensive side-by-side forensic comparison between two analyses.
    Compares prediction discrepancies, calibrated confidence delta, and forensic indicators.
    """
    if id1 == id2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare an analysis to itself. Please provide two distinct analysis IDs."
        )

    a1 = db.query(Analysis).filter(
        Analysis.id == id1,
        Analysis.user_id == current_user.id
    ).first()

    a2 = db.query(Analysis).filter(
        Analysis.id == id2,
        Analysis.user_id == current_user.id
    ).first()

    if not a1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {id1} was not found or does not belong to your account."
        )
    if not a2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {id2} was not found or does not belong to your account."
        )

    if a1.status != AnalysisStatus.completed or a2.status != AnalysisStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both analyses must have status 'completed' before running forensic comparison."
        )

    r1 = a1.result
    r2 = a2.result

    def format_item(a, r):
        indicators = [
            {
                "id": ind.id,
                "type": ind.indicator_type,
                "description": ind.description,
                "severity": ind.severity.value if hasattr(ind.severity, "value") else str(ind.severity),
                "timestamp_seconds": ind.timestamp_seconds,
                "frame_number": ind.frame_number,
                "region_x": ind.region_x,
                "region_y": ind.region_y,
                "region_w": ind.region_w,
                "region_h": ind.region_h,
            }
            for ind in a.indicators
        ]
        return {
            "id": a.id,
            "media_type": a.media_type.value if hasattr(a.media_type, "value") else str(a.media_type),
            "original_filename": a.original_filename,
            "file_size": a.file_size,
            "duration_seconds": a.duration_seconds,
            "width": a.width,
            "height": a.height,
            "prediction": r.prediction.value if r and hasattr(r.prediction, "value") else None,
            "confidence": round(r.confidence, 4) if r else None,
            "risk_level": r.risk_level.value if r and hasattr(r.risk_level, "value") else None,
            "model_name": r.model_name if r else None,
            "model_version": r.model_version if r else None,
            "face_manipulation_score": round(r.face_manipulation_score, 4) if r and r.face_manipulation_score is not None else None,
            "gan_artifact_score": round(r.gan_artifact_score, 4) if r and r.gan_artifact_score is not None else None,
            "temporal_inconsistency_score": round(r.temporal_inconsistency_score, 4) if r and r.temporal_inconsistency_score is not None else None,
            "voice_cloning_score": round(r.voice_cloning_score, 4) if r and r.voice_cloning_score is not None else None,
            "spectral_anomaly_score": round(r.spectral_anomaly_score, 4) if r and r.spectral_anomaly_score is not None else None,
            "indicators": indicators,
            "created_at": a.created_at.isoformat(),
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }

    item1 = format_item(a1, r1)
    item2 = format_item(a2, r2)

    ind_types_1 = set(ind["type"] for ind in item1["indicators"])
    ind_types_2 = set(ind["type"] for ind in item2["indicators"])

    common_ind = list(ind_types_1.intersection(ind_types_2))
    unique_1 = list(ind_types_1 - ind_types_2)
    unique_2 = list(ind_types_2 - ind_types_1)

    conf_delta = abs((item1["confidence"] or 0.0) - (item2["confidence"] or 0.0))

    prediction_match = item1["prediction"] == item2["prediction"]
    risk_match = item1["risk_level"] == item2["risk_level"]

    if prediction_match and item1["prediction"] == "authentic":
        verdict = "Both media artifacts exhibit authentic structural consistency."
    elif prediction_match and item1["prediction"] == "synthetic":
        verdict = f"Both media artifacts show high synthetic manipulation signatures ({conf_delta:.1%} confidence delta)."
    else:
        verdict = f"Discrepancy detected: Item 1 was classified as {item1['prediction']} ({item1['risk_level']} risk) while Item 2 was classified as {item2['prediction']} ({item2['risk_level']} risk)."

    return {
        "item1": item1,
        "item2": item2,
        "comparison": {
            "same_modality": item1["media_type"] == item2["media_type"],
            "prediction_match": prediction_match,
            "risk_match": risk_match,
            "confidence_delta": round(conf_delta, 4),
            "common_indicators": common_ind,
            "item1_unique_indicators": unique_1,
            "item2_unique_indicators": unique_2,
            "forensic_verdict": verdict,
        }
    }
