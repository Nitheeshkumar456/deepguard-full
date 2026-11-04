"""
test_ai_robustness.py — Direct tests for AI inference engine, model architectures, and edge cases.
"""

import io
import os
import sys
import tempfile
import numpy as np
import pytest
import cv2
import torch
from scipy.io import wavfile
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_service import (
    DeepGuardModel,
    run_image_inference,
    run_video_inference,
    run_audio_inference,
    _model_manager,
    get_model_status,
)
from app.services.exceptions import (
    AIServiceError,
    InvalidImageError,
    CorruptFileError,
)
from app.services.video_processor import extract_video_frames
from app.services.audio_processor import generate_spectrogram


class TestModelArchitecture:
    def test_deepguard_model_forward_pass(self):
        model = DeepGuardModel()
        model.eval()
        dummy_input = torch.randn(2, 3, 224, 224)
        with torch.no_grad():
            output = model(dummy_input)
        assert output.shape == (2, 2)
        
        probs = torch.softmax(output, dim=1)
        # Check softmax properties
        sums = probs.sum(dim=1).tolist()
        for s in sums:
            assert pytest.approx(s, 1e-4) == 1.0

    def test_model_manager_singleton(self):
        m = _model_manager
        m.load_model()
        status = get_model_status()
        assert status["loaded"] is True
        assert status["model_name"] is not None


class TestInferencePipelines:
    def test_run_image_inference_real_output(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = f.name
        
        try:
            img = Image.new("RGB", (128, 128), color=(200, 100, 50))
            img.save(temp_path, format="JPEG")

            result = run_image_inference(temp_path)
            assert result.prediction in ("authentic", "synthetic", "uncertain")
            assert 0.0 <= result.confidence <= 1.0
            assert result.risk_level in ("low", "medium", "high", "critical")
            assert result.processing_time_seconds > 0.0
            assert len(result.indicators) > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_run_video_inference_real_output(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            temp_video = f.name

        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video, fourcc, 10.0, (64, 64))
            for i in range(15):
                frame = np.full((64, 64, 3), (i * 15) % 255, dtype=np.uint8)
                out.write(frame)
            out.release()

            result = run_video_inference(temp_video)
            assert result.prediction in ("authentic", "synthetic", "uncertain")
            assert 0.0 <= result.confidence <= 1.0
            assert result.temporal_inconsistency_score is not None
            assert result.processing_time_seconds > 0.0
        finally:
            if os.path.exists(temp_video):
                os.remove(temp_video)

    def test_run_audio_inference_reports_unavailable(self):
        from app.services.exceptions import ModelUnavailableError
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            sr = 22050
            t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
            data = (np.sin(2 * np.pi * 300 * t) * 30000).astype(np.int16)
            wavfile.write(temp_wav, sr, data)

            with pytest.raises(ModelUnavailableError) as exc_info:
                run_audio_inference(temp_wav)
            assert "audio analysis model is unavailable" in str(exc_info.value).lower()
        finally:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)


class TestAIExtractionEdgeCases:
    def test_extract_video_frames_corrupt_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"NOT A REAL VIDEO STREAM")
            corrupt_path = f.name
        
        try:
            with pytest.raises(CorruptFileError):
                extract_video_frames(corrupt_path)
        finally:
            if os.path.exists(corrupt_path):
                os.remove(corrupt_path)

    def test_extract_video_frames_empty_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            corrupt_path = f.name
        
        try:
            with pytest.raises(CorruptFileError):
                extract_video_frames(corrupt_path)
        finally:
            if os.path.exists(corrupt_path):
                os.remove(corrupt_path)

    def test_extract_video_frames_single_frame_video(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            temp_path = f.name
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_path, fourcc, 10.0, (64, 64))
            frame = np.full((64, 64, 3), 128, dtype=np.uint8)
            out.write(frame)
            out.release()

            frames = extract_video_frames(temp_path, num_frames=5)
            assert len(frames) == 1
            for p in frames:
                assert os.path.exists(p)
                assert os.path.getsize(p) > 0
                os.remove(p)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_video_frames_multi_frame_video(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            temp_path = f.name
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_path, fourcc, 10.0, (64, 64))
            for i in range(20):
                frame = np.full((64, 64, 3), (i * 12) % 255, dtype=np.uint8)
                out.write(frame)
            out.release()

            frames = extract_video_frames(temp_path, num_frames=5)
            assert len(frames) == 5
            for p in frames:
                assert os.path.exists(p)
                assert os.path.getsize(p) > 0
                os.remove(p)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_video_frames_real_project_sample(self):
        real_sample = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "ai", "evaluation", "original_c23_subset", "original_sequences", "youtube", "c23", "videos", "033.mp4"
        )
        if os.path.exists(real_sample):
            frames = extract_video_frames(real_sample, num_frames=5)
            assert len(frames) == 5
            for p in frames:
                assert os.path.exists(p)
                assert os.path.getsize(p) > 0
                os.remove(p)

    def test_extract_video_frames_manipulated_project_sample(self):
        fake_sample = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "ai", "evaluation", "manipulated_c23_subset", "manipulated_sequences", "Face2Face", "c23", "videos", "896_128.mp4"
        )
        if os.path.exists(fake_sample):
            frames = extract_video_frames(fake_sample, num_frames=5)
            assert len(frames) == 5
            for p in frames:
                assert os.path.exists(p)
                assert os.path.getsize(p) > 0
                os.remove(p)

    def test_generate_spectrogram_corrupt_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"CORRUPT WAV DATA")
            corrupt_path = f.name

        try:
            with pytest.raises(CorruptFileError):
                generate_spectrogram(corrupt_path)
        finally:
            if os.path.exists(corrupt_path):
                os.remove(corrupt_path)
