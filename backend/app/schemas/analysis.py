"""
analysis.py — Pydantic schemas for analysis API requests and responses.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..models.analysis import (
    MediaType, AnalysisStatus, Prediction, RiskLevel,
    IndicatorSeverity, SubscriptionTier, SubscriptionStatus
)


# ─────────────────────────────────────────────
# Analysis indicator response
# ─────────────────────────────────────────────

class AnalysisIndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    indicator_type: str
    description: str
    severity: IndicatorSeverity
    timestamp_seconds: Optional[float] = None
    frame_number: Optional[int] = None
    region_x: Optional[float] = None
    region_y: Optional[float] = None
    region_w: Optional[float] = None
    region_h: Optional[float] = None
    created_at: datetime


# ─────────────────────────────────────────────
# Analysis result response
# ─────────────────────────────────────────────

class AnalysisResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction: Prediction
    confidence: float
    risk_level: RiskLevel
    model_name: str
    model_version: Optional[str] = None
    face_manipulation_score: Optional[float] = None
    gan_artifact_score: Optional[float] = None
    temporal_inconsistency_score: Optional[float] = None
    voice_cloning_score: Optional[float] = None
    spectral_anomaly_score: Optional[float] = None
    created_at: datetime


# ─────────────────────────────────────────────
# Analysis responses
# ─────────────────────────────────────────────

class AnalysisSummaryOut(BaseModel):
    """Compact analysis card — used in list/history views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_type: MediaType
    original_filename: str
    file_size: Optional[int] = None
    status: AnalysisStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None
    # Flattened result fields (None until completed)
    prediction: Optional[Prediction] = None
    confidence: Optional[float] = None
    risk_level: Optional[RiskLevel] = None


class HeatmapFrameInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    frame_index: int
    timestamp_seconds: float
    original_url: str
    heatmap_url: str


class AnalysisDetailOut(BaseModel):
    """Full analysis detail — includes result, indicators, and explainability heatmap metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    media_type: MediaType
    original_filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    status: AnalysisStatus
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[AnalysisResultOut] = None
    indicators: List[AnalysisIndicatorOut] = []
    heatmap_available: Optional[bool] = None
    heatmap_url: Optional[str] = None
    original_media_url: Optional[str] = None
    heatmap_frames: Optional[List[HeatmapFrameInfo]] = None


class AnalysisSubmitResponse(BaseModel):
    """Immediate response returned after a file is accepted for processing."""
    analysis_id: int
    status: AnalysisStatus
    message: str
    media_type: MediaType
    original_filename: str
    file_size: int


# ─────────────────────────────────────────────
# History / list response
# ─────────────────────────────────────────────

class AnalysisHistoryOut(BaseModel):
    items: List[AnalysisSummaryOut]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────
# Delete response
# ─────────────────────────────────────────────

class DeleteResponse(BaseModel):
    message: str


# ─────────────────────────────────────────────
# Notification & Subscription schemas
# ─────────────────────────────────────────────

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    body: str
    is_read: bool
    related_analysis_id: Optional[int] = None
    created_at: datetime


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str
    status: str
    used_analyses: int
    total_analyses: int

