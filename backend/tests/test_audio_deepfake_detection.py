import io
import math
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app
from app.models.auth import User
from app.models.analysis import Analysis, AnalysisResult, AnalysisIndicator, Notification
from app.utils.auth_utils import create_access_token
from app.utils.security import get_password_hash
from app.services.audio_preprocessor import (
    preprocess_audio,
    TARGET_SAMPLE_RATE,
    TARGET_SAMPLES,
)
from app.services.audio_detector import AudioDeepfakeDetector
from tests.conftest import TestingSessionLocal


def generate_synthesized_audio_bytes(
    duration: float = 2.0,
    sample_rate: int = 16000,
    tone_freqs: list = [220, 440, 880],
    is_silent: bool = False,
    noise_level: float = 0.01,
) -> bytes:
    """Helper to generate in-memory WAV audio bytes for testing."""
    total_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, total_samples, endpoint=False)

    if is_silent:
        audio = np.zeros(total_samples, dtype=np.float32)
    else:
        audio = np.zeros(total_samples, dtype=np.float32)
        for f in tone_freqs:
            audio += (0.4 / len(tone_freqs)) * np.sin(2 * np.pi * f * t).astype(np.float32)
        if noise_level > 0:
            audio += np.random.normal(0, noise_level, total_samples).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV")
    return buf.getvalue()


@pytest.fixture(scope="module")
def audio_test_user():
    db = TestingSessionLocal()
    db.query(User).filter(User.email == "audio_tester@deepguard.ai").delete(synchronize_session=False)
    db.commit()

    user = User(
        name="Audio Tester",
        email="audio_tester@deepguard.ai",
        hashed_password=get_password_hash("StrongSecret123!"),
        is_active=True,
        is_verified=True,
        version=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    ctx = {"user": user, "token": token}
    db.close()
    return ctx


def test_audio_preprocessor_resampling_and_windowing(tmp_path):
    """Test audio preprocessor handles arbitrary sample rates and converts to 16kHz (N, 64600) windows."""
    audio_path = tmp_path / "test_48k.wav"
    wav_bytes = generate_synthesized_audio_bytes(duration=1.5, sample_rate=48000, tone_freqs=[300, 600])
    audio_path.write_bytes(wav_bytes)

    preprocessed = preprocess_audio(str(audio_path))
    assert preprocessed.original_sample_rate == 48000
    assert preprocessed.duration_seconds == 1.5
    assert preprocessed.waveform_windows.shape == (1, TARGET_SAMPLES)
    assert not preprocessed.is_silent
    assert preprocessed.rms_energy > 0.01


def test_audio_preprocessor_silence_detection(tmp_path):
    """Test silence detection correctly tags zero or near-zero energy recordings."""
    silent_path = tmp_path / "silent.wav"
    wav_bytes = generate_synthesized_audio_bytes(duration=1.0, is_silent=True)
    silent_path.write_bytes(wav_bytes)

    preprocessed = preprocess_audio(str(silent_path))
    assert preprocessed.is_silent is True
    assert preprocessed.rms_energy < 1e-4


def test_audio_preprocessor_rejects_very_short_clips(tmp_path):
    """Test files below 0.25 seconds are rejected with CorruptFileError."""
    short_path = tmp_path / "short.wav"
    wav_bytes = generate_synthesized_audio_bytes(duration=0.1, sample_rate=16000)
    short_path.write_bytes(wav_bytes)

    with pytest.raises(Exception) as exc_info:
        preprocess_audio(str(short_path))
    assert "too short" in str(exc_info.value).lower()


def test_aasist_model_inference_execution(tmp_path):
    """Test direct AASIST model execution generates valid probabilities and forensic indicators."""
    test_path = tmp_path / "sample_speech.wav"
    wav_bytes = generate_synthesized_audio_bytes(duration=2.5, tone_freqs=[250, 500, 1000])
    test_path.write_bytes(wav_bytes)

    detector = AudioDeepfakeDetector()
    result = detector.detect(str(test_path))

    assert result.prediction in ("authentic", "synthetic", "uncertain")
    assert 0.0 <= result.confidence <= 1.0
    assert result.risk_level in ("low", "medium", "high", "critical")
    assert result.model_name == "AASIST-GraphAttention"
    assert result.model_version == "v1.0"
    assert result.voice_cloning_score is not None
    assert result.spectral_anomaly_score is not None
    assert len(result.indicators) > 0
    assert result.processing_time_seconds > 0.0


def test_silent_audio_returns_uncertain_with_info_indicator(tmp_path):
    """Test silent audio does not produce a false positive or negative, but returns inconclusive status."""
    silent_path = tmp_path / "zero_signal.wav"
    silent_path.write_bytes(generate_synthesized_audio_bytes(duration=1.0, is_silent=True))

    detector = AudioDeepfakeDetector()
    result = detector.detect(str(silent_path))

    assert result.prediction == "uncertain"
    assert result.risk_level == "low"
    assert any("silence" in ind.indicator_type.lower() for ind in result.indicators)


def test_post_audio_endpoint_and_async_processing(audio_test_user):
    """Test POST /api/analysis/audio uploads audio, queues analysis, and persists result."""
    client = TestClient(app)
    token = audio_test_user["token"]
    headers = {"Authorization": f"Bearer {token}"}

    wav_bytes = generate_synthesized_audio_bytes(duration=2.0, sample_rate=16000, tone_freqs=[440, 880])
    files = {"file": ("recorded_speech.wav", io.BytesIO(wav_bytes), "audio/wav")}

    # Connect WebSocket to receive live sync completion event
    with client.websocket_connect(f"/api/ws?token={token}") as ws:
        ws.receive_json()  # Handshake

        # Submit audio
        resp = client.post("/api/analysis/audio", files=files, headers=headers)
        assert resp.status_code == 202
        submit_data = resp.json()
        assert submit_data["media_type"] == "audio"
        analysis_id = submit_data["analysis_id"]

        # Receive WebSocket completion event
        received_events = []
        for _ in range(5):
            try:
                ev = ws.receive_json()
                received_events.append(ev.get("event"))
                if ev.get("event") == "analysis.completed":
                    break
            except Exception:
                break

        assert "media.uploaded" in received_events or "analysis.completed" in received_events

        # Fetch detail
        detail_resp = client.get(f"/api/analysis/{analysis_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == analysis_id
        assert detail["media_type"] == "audio"
        assert detail["status"] == "completed"
        assert detail["result"]["model_name"] == "AASIST-GraphAttention"
        assert detail["result"]["prediction"] in ("authentic", "synthetic", "uncertain")
        assert len(detail["indicators"]) > 0


def test_audio_analysis_history_filtering(audio_test_user):
    """Test scan history correctly lists and filters audio analysis records."""
    client = TestClient(app)
    token = audio_test_user["token"]
    headers = {"Authorization": f"Bearer {token}"}

    history_resp = client.get("/api/analysis/history?media_type=audio&page=1&page_size=10", headers=headers)
    assert history_resp.status_code == 200
    items = history_resp.json()["items"]
    assert len(items) > 0
    assert all(item["media_type"] == "audio" for item in items)
