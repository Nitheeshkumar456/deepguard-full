import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    ForeignKey, Enum, Text, BigInteger
)
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class MediaType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"


class AnalysisStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Prediction(str, enum.Enum):
    authentic = "authentic"
    synthetic = "synthetic"
    uncertain = "uncertain"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IndicatorSeverity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SubscriptionTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"
    trial = "trial"


class NotificationCategory(str, enum.Enum):
    analysis = "analysis"
    security = "security"
    billing = "billing"
    system = "system"


# ─────────────────────────────────────────────
# Analysis Models
# ─────────────────────────────────────────────

class Analysis(Base):
    """Represents a media analysis job submitted by a user."""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Media metadata
    media_type = Column(Enum(MediaType), nullable=False)
    original_filename = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=True)           # bytes
    mime_type = Column(String(128), nullable=True)
    duration_seconds = Column(Float, nullable=True)         # video/audio only
    width = Column(Integer, nullable=True)                  # image/video only
    height = Column(Integer, nullable=True)                 # image/video only
    storage_path = Column(String(1024), nullable=True)      # internal storage ref

    # Processing lifecycle
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.queued, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)          # seconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="analyses")
    result = relationship("AnalysisResult", back_populates="analysis", uselist=False, cascade="all, delete-orphan")
    indicators = relationship("AnalysisIndicator", back_populates="analysis", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="analysis", uselist=False, cascade="all, delete-orphan")


class AnalysisResult(Base):
    """Stores the prediction output of an AI model for a completed analysis."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Prediction
    prediction = Column(Enum(Prediction), nullable=False)
    confidence = Column(Float, nullable=False)              # 0.0 – 1.0
    risk_level = Column(Enum(RiskLevel), nullable=False)

    # Model metadata
    model_name = Column(String(256), nullable=False)
    model_version = Column(String(64), nullable=True)

    # Per-modality scores (nullable — populated only for relevant media type)
    face_manipulation_score = Column(Float, nullable=True)  # image / video
    gan_artifact_score = Column(Float, nullable=True)       # image / video
    temporal_inconsistency_score = Column(Float, nullable=True)  # video
    voice_cloning_score = Column(Float, nullable=True)      # audio
    spectral_anomaly_score = Column(Float, nullable=True)   # audio

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="result")


class AnalysisIndicator(Base):
    """A single forensic indicator detected during analysis."""
    __tablename__ = "analysis_indicators"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    indicator_type = Column(String(128), nullable=False)    # e.g. "blending_artifact", "frequency_anomaly"
    description = Column(Text, nullable=False)
    severity = Column(Enum(IndicatorSeverity), nullable=False)

    # Spatial / temporal location context (nullable depending on media type)
    timestamp_seconds = Column(Float, nullable=True)        # video / audio — when in media
    frame_number = Column(Integer, nullable=True)           # video — specific frame
    region_x = Column(Float, nullable=True)                 # image / video — bounding box x (0-1 normalised)
    region_y = Column(Float, nullable=True)                 # image / video — bounding box y
    region_w = Column(Float, nullable=True)                 # bounding box width
    region_h = Column(Float, nullable=True)                 # bounding box height

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="indicators")


# ─────────────────────────────────────────────
# Report Model
# ─────────────────────────────────────────────

class Report(Base):
    """A formal report generated for a completed analysis."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(512), nullable=True)
    summary = Column(Text, nullable=True)
    pdf_path = Column(String(1024), nullable=True)          # generated PDF storage path

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="report")
    user = relationship("User", back_populates="reports")


# ─────────────────────────────────────────────
# Usage Statistics Model
# ─────────────────────────────────────────────

class UsageStatistics(Base):
    """Monthly usage record for a user (updated on analysis completion)."""
    __tablename__ = "usage_statistics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)                 # 1–12

    total_analyses = Column(Integer, default=0, nullable=False)
    image_analyses = Column(Integer, default=0, nullable=False)
    video_analyses = Column(Integer, default=0, nullable=False)
    audio_analyses = Column(Integer, default=0, nullable=False)

    authentic_count = Column(Integer, default=0, nullable=False)
    synthetic_count = Column(Integer, default=0, nullable=False)
    uncertain_count = Column(Integer, default=0, nullable=False)

    total_file_size_bytes = Column(BigInteger, default=0, nullable=False)
    total_processing_seconds = Column(Float, default=0.0, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="usage_statistics")


# ─────────────────────────────────────────────
# Notification Model
# ─────────────────────────────────────────────

class Notification(Base):
    """In-app notifications for a user."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    category = Column(Enum(NotificationCategory), nullable=False)
    title = Column(String(256), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    # Optional link to related entity
    related_analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


# ─────────────────────────────────────────────
# Subscription Model
# ─────────────────────────────────────────────

class Subscription(Base):
    """User subscription plan and billing details."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.free, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.active, nullable=False)

    # Limits (nullable = unlimited)
    monthly_analysis_limit = Column(Integer, nullable=True)    # None = unlimited
    max_file_size_mb = Column(Integer, nullable=True)

    # Billing cycle
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # External billing provider reference
    external_subscription_id = Column(String(256), nullable=True)
    external_customer_id = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscription")
