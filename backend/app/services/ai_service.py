"""
ai_service.py — AI inference integration layer for the DeepGuard backend.

Bridges the backend analysis pipeline with the PyTorch model:
  1. Model lifecycle management (load once, cache, device selection)
  2. Image inference execution with timeout protection
  3. Result aggregation (probabilities → prediction + confidence + risk level)
  4. Forensic indicator generation from actual model outputs

CRITICAL DESIGN RULES:
  - NEVER generate random confidence values.
  - NEVER return fabricated detection indicators.
  - ALL outputs come directly from model inference.
  - When model is unavailable, raise ModelUnavailableError — don't fake results.
"""

import os
import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0

from ..config import settings
from .exceptions import (
    ModelUnavailableError,
    InferenceError,
    InferenceTimeoutError,
)
from .image_preprocessor import preprocess_image, PreprocessedImage

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data structures for inference results
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ForensicIndicator:
    """A single forensic indicator derived from model analysis."""
    indicator_type: str
    description: str
    severity: str  # "info" | "low" | "medium" | "high" | "critical"
    region_x: Optional[float] = None
    region_y: Optional[float] = None
    region_w: Optional[float] = None
    region_h: Optional[float] = None


@dataclass
class InferenceResult:
    """Complete result from a single image/video/audio inference pass."""
    prediction: str        # "authentic" | "synthetic" | "uncertain"
    confidence: float      # 0.0 – 1.0
    risk_level: str        # "low" | "medium" | "high" | "critical"
    model_name: str
    model_version: str
    probabilities: Dict[str, float] = field(default_factory=dict)  # raw class probs
    face_manipulation_score: Optional[float] = None
    gan_artifact_score: Optional[float] = None
    temporal_inconsistency_score: Optional[float] = None
    voice_cloning_score: Optional[float] = None
    spectral_anomaly_score: Optional[float] = None
    indicators: List[ForensicIndicator] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    device_used: str = "cpu"
    evidence_category: str = "INCONCLUSIVE"
    limitations: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Model definition (inline to avoid import path issues with ai/ module)
# Mirrors ai/src/model.py — DeepGuardModel
# ─────────────────────────────────────────────────────────────────────────────

class DeepGuardModel(nn.Module):
    """EfficientNet-B0 model for deepfake detection.
    Matches the architecture and state_dict layer names in efficientnet_b0_ffpp_c23.pth.
    Class 0 = Real (Authentic), Class 1 = Fake (Synthetic).
    """

    def __init__(self):
        super().__init__()
        base = efficientnet_b0(weights=None)
        self.features = base.features
        self.avgpool = base.avgpool
        self.classifier = base.classifier
        self.classifier[1] = nn.Linear(self.classifier[1].in_features, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

# Alias for backward compatibility
EfficientNetModel = DeepGuardModel

# ─────────────────────────────────────────────────────────────────────────────
# Singleton model manager
# ─────────────────────────────────────────────────────────────────────────────

class _ModelManager:
    """
    Thread-safe singleton that manages model loading and caching.
    The model is loaded once on first use and kept in memory.
    """

    def __init__(self):
        self._model: Optional[nn.Module] = None
        self._device: Optional[torch.device] = None
        self._lock = threading.Lock()
        self._loaded = False
        self._model_name: str = ""
        self._model_version: str = ""
        self._has_trained_weights: bool = False

    @property
    def device(self) -> torch.device:
        if self._device is None:
            self._resolve_device()
        return self._device

    def _resolve_device(self) -> None:
        """Select compute device based on configuration."""
        device_config = getattr(settings, "AI_DEVICE", "auto")
        if device_config == "auto":
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self._device = torch.device(device_config)
        logger.info("AI device resolved: %s", self._device)

    def load_model(self) -> nn.Module:
        """
        Load the model, optionally with trained weights.
        Thread-safe — only loads once.

        Returns the loaded model.
        Raises ModelUnavailableError if model instantiation fails.
        """
        if self._loaded and self._model is not None:
            return self._model

        with self._lock:
            # Double-check after acquiring lock
            if self._loaded and self._model is not None:
                return self._model

            try:
                model = EfficientNetModel()
                device = self.device

                # Attempt to load trained weights; must exist
                model_path = getattr(settings, "AI_MODEL_PATH", "")
                if model_path and os.path.isfile(model_path):
                    try:
                        state_dict = torch.load(
                            model_path,
                            map_location=device,
                            weights_only=True,
                        )
                        model.load_state_dict(state_dict)
                        self._has_trained_weights = True
                        logger.info("Loaded trained weights from: %s", model_path)
                    except Exception as exc:
                        logger.error(
                            "Failed to load trained weights from %s: %s. "
                            "Model initialization aborted.",
                            model_path, exc,
                        )
                        raise ModelUnavailableError(
                            f"Could not load trained AI model weights from {model_path}: {exc}"
                        )
                else:
                    logger.error(
                        "AI_MODEL_PATH not set or weights file missing. "
                        "Model cannot be initialized without trained weights."
                    )
                    raise ModelUnavailableError(
                        "AI model path not configured or weights file not found. "
                        "Set AI_MODEL_PATH to a valid pretrained checkpoint."
                    )

                model.to(device)
                model.eval()

                self._model = model
                self._model_name = getattr(settings, "AI_MODEL_NAME", "deepguard-cnn-v1")
                self._model_version = "1.0.0-trained" if self._has_trained_weights else "1.0.0-untrained"
                self._loaded = True

                logger.info(
                    "Model ready: name=%s, version=%s, device=%s, trained=%s",
                    self._model_name, self._model_version, device, self._has_trained_weights,
                )
                return self._model

            except Exception as exc:
                logger.error("Failed to instantiate AI model: %s", exc)
                raise ModelUnavailableError(
                    f"Could not initialize the AI model: {exc}"
                )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def has_trained_weights(self) -> bool:
        return self._has_trained_weights


# Global singleton
_model_manager = _ModelManager()


# ─────────────────────────────────────────────────────────────────────────────
# Risk classification — pure function, no randomness
# ─────────────────────────────────────────────────────────────────────────────

def classify_risk(prediction: str, confidence: float) -> str:
    """
    Determine risk level from prediction label and confidence score.

    Risk matrix:
      - authentic + high confidence → low
      - authentic + low confidence  → medium (uncertain authenticity)
      - synthetic + low confidence  → medium
      - synthetic + moderate conf   → high
      - synthetic + high confidence → critical
      - uncertain                   → medium
    """
    if prediction == "uncertain":
        return "medium"

    if prediction == "authentic":
        if confidence >= 0.8:
            return "low"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "medium"  # Low confidence authentic = still some risk

    if prediction == "synthetic":
        if confidence >= 0.9:
            return "critical"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "medium"

    return "medium"  # Fallback


def _determine_prediction(prob_authentic: float, prob_deepfake: float) -> str:
    """
    Map raw probabilities to a prediction label.
    Uses a confidence margin to flag uncertain results honestly.
    """
    margin = abs(prob_authentic - prob_deepfake)

    # If the margin between the two classes is very small, it's uncertain
    if margin < 0.1:
        return "uncertain"

    if prob_authentic > prob_deepfake:
        return "authentic"
    else:
        return "synthetic"


# ─────────────────────────────────────────────────────────────────────────────
# Forensic indicator generation — derived from actual model outputs
# ─────────────────────────────────────────────────────────────────────────────

def _generate_indicators(
    prob_authentic: float,
    prob_deepfake: float,
    prediction: str,
    confidence: float,
    feature_stats: Optional[Dict[str, float]] = None,
) -> List[ForensicIndicator]:
    """
    Generate forensic indicators based on actual model output analysis.

    These indicators are DERIVED from real model outputs, not fabricated:
    - Probability distribution analysis
    - Feature activation statistics (from intermediate layers)
    - Confidence level assessment

    Returns an empty list if there's nothing notable to report.
    """
    indicators: List[ForensicIndicator] = []

    # ── 1. Report the model's confidence assessment ─────────────────────────
    if prediction == "synthetic":
        severity = "critical" if confidence >= 0.9 else "high" if confidence >= 0.7 else "medium"
        indicators.append(ForensicIndicator(
            indicator_type="deepfake_probability",
            description=(
                f"Model assigns {prob_deepfake:.1%} probability to synthetic/deepfake "
                f"classification with {confidence:.1%} confidence."
            ),
            severity=severity,
        ))

    elif prediction == "authentic":
        indicators.append(ForensicIndicator(
            indicator_type="authenticity_assessment",
            description=(
                f"Model assigns {prob_authentic:.1%} probability to authentic "
                f"classification with {confidence:.1%} confidence."
            ),
            severity="info",
        ))

    elif prediction == "uncertain":
        indicators.append(ForensicIndicator(
            indicator_type="classification_uncertainty",
            description=(
                f"Model output is ambiguous: authentic={prob_authentic:.1%}, "
                f"synthetic={prob_deepfake:.1%}. The margin is too narrow "
                f"for reliable classification."
            ),
            severity="medium",
        ))

    # ── 2. Feature-based indicators (from intermediate activations) ─────────
    if feature_stats:
        mean_activation = feature_stats.get("mean_activation", 0.0)
        std_activation = feature_stats.get("std_activation", 0.0)

        # High activation variance can indicate anomalous patterns
        if std_activation > 0.5:
            indicators.append(ForensicIndicator(
                indicator_type="feature_anomaly",
                description=(
                    f"Feature activation analysis: mean={mean_activation:.4f}, "
                    f"std={std_activation:.4f}. Elevated variance in feature "
                    f"responses may indicate processing artifacts."
                ),
                severity="low" if prediction == "authentic" else "medium",
            ))

    return indicators


# ─────────────────────────────────────────────────────────────────────────────
# Core inference function
# ─────────────────────────────────────────────────────────────────────────────

def run_image_inference(file_path: str) -> InferenceResult:
    """
    Execute image forensics pipeline with dual-path face and global neural analysis,
    2D FFT spectral anomaly estimation, and calibrated multi-model fusion.
    """
    from .image_forensics import get_image_forensics_engine
    
    start_time = time.monotonic()
    timeout_seconds = getattr(settings, "AI_INFERENCE_TIMEOUT", 30)
    engine = get_image_forensics_engine(model_manager=_model_manager)
    
    inference_result: Optional[Any] = None
    inference_error: Optional[Exception] = None

    def _run():
        nonlocal inference_result, inference_error
        try:
            inference_result = engine.analyze_image(file_path)
        except Exception as exc:
            inference_error = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        elapsed = time.monotonic() - start_time
        raise InferenceTimeoutError(
            f"Image inference timed out after {elapsed:.1f}s (limit: {timeout_seconds}s)."
        )

    if inference_error is not None:
        from .exceptions import DeepGuardException
        if isinstance(inference_error, DeepGuardException):
            raise inference_error
        raise InferenceError(f"Image forensic analysis failed: {inference_error}")

    if inference_result is None:
        raise InferenceError("Image forensic analysis produced no output.")

    elapsed = time.monotonic() - start_time
    res = inference_result

    forensic_indicators = []
    for ind in res.indicators:
        forensic_indicators.append(ForensicIndicator(
            indicator_type=ind["indicator_type"],
            description=ind["description"],
            severity=ind.get("severity", "medium"),
            region_x=ind.get("region_x"),
            region_y=ind.get("region_y"),
            region_w=ind.get("region_w"),
            region_h=ind.get("region_h"),
        ))

    return InferenceResult(
        prediction=res.prediction,
        confidence=res.confidence,
        risk_level=res.risk_level,
        model_name=_model_manager.model_name,
        model_version=_model_manager.model_version,
        probabilities=res.probabilities,
        face_manipulation_score=res.face_manipulation_score,
        gan_artifact_score=res.gan_artifact_score,
        spectral_anomaly_score=res.spectral_anomaly_score,
        indicators=forensic_indicators,
        processing_time_seconds=round(elapsed, 4),
        device_used=str(_model_manager.device),
        evidence_category=res.evidence_category,
        limitations=res.limitations,
    )


def run_video_inference(file_path: str) -> InferenceResult:
    """
    Execute video forensics pipeline:
      1. Scene-cut aware keyframe sampling.
      2. Per-frame face manipulation detection.
      3. Inter-frame temporal inconsistency analysis.
      4. Audio track demuxing & AASIST cross-modal speech verification.
    """
    from .video_forensics import get_video_forensics_engine

    start_time = time.monotonic()
    timeout_seconds = getattr(settings, "AI_INFERENCE_TIMEOUT", 60)
    engine = get_video_forensics_engine(model_manager=_model_manager)

    video_result: Optional[Any] = None
    inference_error: Optional[Exception] = None

    def _run():
        nonlocal video_result, inference_error
        try:
            video_result = engine.analyze_video(file_path)
        except Exception as exc:
            inference_error = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        elapsed = time.monotonic() - start_time
        raise InferenceTimeoutError(
            f"Video inference timed out after {elapsed:.1f}s (limit: {timeout_seconds}s)."
        )

    if inference_error is not None:
        from .exceptions import DeepGuardException
        if isinstance(inference_error, DeepGuardException):
            raise inference_error
        raise InferenceError(f"Video forensic analysis failed: {inference_error}")

    if video_result is None:
        raise InferenceError("Video forensic analysis produced no output.")

    elapsed = time.monotonic() - start_time
    vres = video_result

    forensic_indicators = []
    for ind in vres.indicators:
        forensic_indicators.append(ForensicIndicator(
            indicator_type=ind["indicator_type"],
            description=ind["description"],
            severity=ind.get("severity", "medium"),
            region_x=ind.get("region_x"),
            region_y=ind.get("region_y"),
            region_w=ind.get("region_w"),
            region_h=ind.get("region_h"),
        ))

    return InferenceResult(
        prediction=vres.prediction,
        confidence=vres.confidence,
        risk_level=vres.risk_level,
        model_name=_model_manager.model_name,
        model_version=_model_manager.model_version,
        probabilities={
            "authentic": round(1.0 - vres.confidence if vres.prediction == "synthetic" else vres.confidence, 4),
            "deepfake": round(vres.confidence if vres.prediction == "synthetic" else 1.0 - vres.confidence, 4),
        },
        face_manipulation_score=vres.face_manipulation_score,
        temporal_inconsistency_score=vres.temporal_inconsistency_score,
        voice_cloning_score=vres.audio_spoof_score,
        spectral_anomaly_score=vres.cross_modal_inconsistency,
        indicators=forensic_indicators,
        processing_time_seconds=round(elapsed, 4),
        device_used=str(_model_manager.device),
        evidence_category=vres.evidence_category,
        limitations=vres.limitations,
    )

def run_audio_inference(file_path: str) -> InferenceResult:
    """
    Execute audio inference pipeline using the AASIST audio deepfake detection model.
    """
    from .audio_detector import run_audio_inference as _exec_audio_inference
    return _exec_audio_inference(file_path)


def get_model_status() -> Dict[str, Any]:
    """
    Return the current model status for health check endpoints.
    Does not load the model — only reports cached state.
    """
    return {
        "loaded": _model_manager._loaded,
        "model_name": _model_manager.model_name or None,
        "model_version": _model_manager.model_version or None,
        "has_trained_weights": _model_manager.has_trained_weights if _model_manager._loaded else None,
        "device": str(_model_manager.device) if _model_manager._device else None,
    }
