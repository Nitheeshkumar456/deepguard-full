"""
test_model_regression.py — Regression and integration tests for DeepGuard AI v2.0.

Validates:
1. AI Model Loading & v2 Checkpoint verification
2. Standalone Facial Morphing Detector execution & signal bounds
3. Full image inference pipeline & calibrated fusion
4. FastAPI endpoints & response schemas
5. Database schema migration for morphing score columns
6. Strict backward compatibility
"""

import os
import sys
import numpy as np
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.main import app
from app.services.morphing_detector import get_morphing_detector
from app.services.ai_service import get_model_status, run_image_inference, _model_manager
from app.schemas.analysis import AnalysisResultOut


client = TestClient(app)


def test_ai_model_status_and_version():
    """Verify AI model loads upgraded weights and returns valid model metadata."""
    # Ensure model is initialized
    _model_manager.load_model()
    status = get_model_status()
    assert status["loaded"] is True
    assert status["has_trained_weights"] is True
    assert status["model_version"] in ("2.0.0", "3.0.0", "4.0.0", "5.0.0")
    assert any(ckpt in settings.AI_MODEL_PATH for ckpt in ("efficientnet_b0_v2_finetuned.pth", "efficientnet_b0_v3_multimodal.pth", "efficientnet_b0_v4_expanded_2k.pth", "efficientnet_b0_v5_video.pth"))


def test_morphing_detector_standalone():
    """Verify facial morphing detector computes all 5 signals with values in [0.0, 1.0]."""
    detector = get_morphing_detector()
    assert detector is not None

    # Generate synthetic RGB test pattern simulating a face crop
    dummy_bgr = np.zeros((224, 224, 3), dtype=np.uint8)
    dummy_bgr[50:180, 50:180] = [180, 120, 90]  # center skin-like region
    dummy_bgr[40:50, 40:190] = [30, 20, 10]    # high-contrast boundary artifact

    result = detector.analyze(dummy_bgr, face_bbox_xywh=(50, 50, 130, 130))

    assert "composite_morphing_score" in result
    assert 0.0 <= result["composite_morphing_score"] <= 1.0
    assert 0.0 <= result["boundary_discontinuity_score"] <= 1.0
    assert 0.0 <= result["texture_uniformity_score"] <= 1.0
    assert 0.0 <= result["color_mismatch_score"] <= 1.0
    assert 0.0 <= result["edge_coherence_score"] <= 1.0
    assert 0.0 <= result["lbp_entropy_score"] <= 1.0
    assert isinstance(result["indicators"], list)


def test_image_inference_pipeline_on_real_and_fake():
    """Verify end-to-end image inference produces all v2 metrics and valid predictions."""
    test_fake_dir = PROJECT_ROOT / "ai" / "datasets" / "test" / "fake"
    test_real_dir = PROJECT_ROOT / "ai" / "datasets" / "test" / "real"

    sample_fake = next(test_fake_dir.glob("*.jpg"), None)
    sample_real = next(test_real_dir.glob("*.jpg"), None)

    assert sample_fake is not None, "Test fake image missing"
    assert sample_real is not None, "Test real image missing"

    for img_path, expected_label in [(sample_fake, "synthetic"), (sample_real, "authentic")]:
        res = run_image_inference(str(img_path))

        assert res.prediction in ("authentic", "synthetic", "uncertain")
        assert 0.0 <= res.confidence <= 1.0
        assert res.risk_level in ("low", "medium", "high", "critical")
        assert res.processing_time_seconds > 0.0

        # v2 additive morphing scores
        assert res.morphing_score is not None
        assert 0.0 <= res.morphing_score <= 1.0
        assert res.boundary_discontinuity_score is not None
        assert res.lbp_entropy_score is not None
        assert res.color_mismatch_score is not None


def test_api_health_and_status_endpoints():
    """Verify FastAPI public health and system status endpoints."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    resp = client.get("/api/v1/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["version"] == "2.0.0"

    resp = client.get("/api/v1/ai/status")
    assert resp.status_code == 200
    ai_stat = resp.json()
    assert ai_stat["loaded"] is True
    assert ai_stat["model_version"] in ("2.0.0", "3.0.0", "4.0.0", "5.0.0")


def test_direct_ai_prediction_endpoint():
    """Verify /api/v1/ai/predict processes an upload and returns valid classification."""
    test_fake = next((PROJECT_ROOT / "ai" / "datasets" / "test" / "fake").glob("*.jpg"), None)
    assert test_fake is not None

    with open(test_fake, "rb") as f:
        resp = client.post(
            "/api/v1/ai/predict",
            files={"file": ("test.jpg", f, "image/jpeg")}
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["prediction"] in (0, 1)
    assert data["label"] in ("Real", "Fake")
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["probabilities"]) == 2
    assert "inference_time_ms" in data


def test_analysis_result_schema_backward_compatibility():
    """Verify AnalysisResultOut maintains backward compatibility with optional morphing fields."""
    legacy_payload = {
        "id": 101,
        "prediction": "synthetic",
        "confidence": 0.94,
        "risk_level": "high",
        "model_name": "EfficientNet-B0",
        "created_at": "2026-11-10T12:00:00",
    }
    obj = AnalysisResultOut.model_validate(legacy_payload)
    assert obj.id == 101
    assert obj.morphing_score is None

    v2_payload = {
        **legacy_payload,
        "model_name": "EfficientNet-B0-v2",
        "model_version": "2.0.0",
        "morphing_score": 0.8123,
        "boundary_discontinuity_score": 0.745,
        "lbp_entropy_score": 0.32,
        "color_mismatch_score": 0.65,
    }
    v2_obj = AnalysisResultOut.model_validate(v2_payload)
    assert v2_obj.morphing_score == 0.8123
    assert v2_obj.color_mismatch_score == 0.65


def test_video_forensics_pipeline():
    """Verify video analysis keyframe extraction, timestamps, face manipulation and morphing scores."""
    from app.services.video_forensics import get_video_forensics_engine

    video_files = list((PROJECT_ROOT / "backend" / "uploads" / "video").glob("*.mp4"))
    if not video_files:
        video_files = list((PROJECT_ROOT / "ai" / "evaluation" / "manipulated_c23_subset").glob("*.mp4"))

    assert len(video_files) > 0, "No test video files found"

    engine = get_video_forensics_engine()
    res = engine.analyze_video(str(video_files[0]))

    assert res.prediction in ("authentic", "synthetic", "uncertain")
    assert 0.0 <= res.confidence <= 1.0
    assert res.risk_level in ("low", "medium", "high", "critical")
    assert res.duration_seconds > 0.0
    assert res.total_frames_sampled > 0
    assert 0.0 <= res.face_manipulation_score <= 1.0
    assert 0.0 <= res.temporal_inconsistency_score <= 1.0

    # Keyframes have valid timestamps and bounded indices
    for fe in res.frame_evidences:
        assert fe.timestamp_seconds >= 0.0
        assert 0.0 <= fe.manipulation_score <= 1.0

    # Suspicious timestamps and visual explanations
    assert hasattr(res, "suspicious_timestamps")
    assert hasattr(res, "frame_level_predictions")
    assert hasattr(res, "visual_explanations")
    assert isinstance(res.suspicious_timestamps, list)
    assert isinstance(res.frame_level_predictions, list)
    assert isinstance(res.visual_explanations, list)

    # Morphing scores verified if present
    if res.morphing_score is not None:
        assert 0.0 <= res.morphing_score <= 1.0


def test_audio_tampering_and_splicing_detection():
    """Verify signal-level audio tampering detector flags splices with accurate timestamps."""
    from app.services.audio_tampering_detector import get_audio_tampering_detector

    sr = 16000
    t = np.linspace(0, 3.0, int(3.0 * sr), endpoint=False)

    detector = get_audio_tampering_detector()

    # 1. Continuous clean audio
    clean = (0.5 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    clean_res = detector.analyze(clean, sr)
    assert 0.0 <= clean_res["composite_tampering_score"] <= 1.0
    assert len(clean_res["splice_points"]) == 0

    # 2. Spliced audio: segment A abruptly joined with segment B at 1.5s
    seg_a = 0.6 * np.sin(2 * np.pi * 150 * t[:len(t)//2]) + 0.01 * np.random.normal(0, 1, len(t)//2)
    seg_b = 0.2 * np.sin(2 * np.pi * 600 * t[len(t)//2:]) + 0.15 * np.random.normal(0, 1, len(t) - len(t)//2)
    spliced = np.concatenate([seg_a, seg_b]).astype(np.float32)

    spliced_res = detector.analyze(spliced, sr)
    assert spliced_res["splicing_score"] >= 0.50
    assert len(spliced_res["splice_points"]) > 0
    # Splice point must be detected within 150ms of 1.5s
    assert any(abs(pt - 1.5) < 0.15 for pt in spliced_res["splice_points"])


def test_audio_inference_end_to_end():
    """Verify AASIST audio deepfake detection and tampering integration."""
    from app.services.audio_detector import run_audio_inference

    audio_files = list((PROJECT_ROOT / "backend" / "uploads" / "audio").glob("*.wav"))
    assert len(audio_files) > 0, "No test audio files found"

    res = run_audio_inference(str(audio_files[0]))

    assert res.prediction in ("authentic", "synthetic", "uncertain")
    assert 0.0 <= res.confidence <= 1.0
    assert res.risk_level in ("low", "medium", "high", "critical")
    assert res.voice_cloning_score is not None
    assert 0.0 <= res.voice_cloning_score <= 1.0
    assert res.spectral_anomaly_score is not None
    assert 0.0 <= res.spectral_anomaly_score <= 1.0
    assert len(res.indicators) > 0

