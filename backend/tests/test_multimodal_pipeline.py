"""
test_multimodal_pipeline.py — Comprehensive tests for multimodal analysis (Image, Video, Audio).
"""

import io
import os
import tempfile
import numpy as np
import pytest
import cv2
from scipy.io import wavfile
from app.models.auth import User


@pytest.fixture(scope="module")
def user1_token(client, setup_test_suite_database):
    email = "user1@example.com"
    pwd = "User1Password123!"
    client.post("/api/auth/register", json={"name": "User One", "email": email, "password": pwd, "confirm_password": pwd})
    
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    u = db.query(User).filter(User.email == email).first()
    if u:
        u.is_verified = True
        db.commit()
    db.close()
    
    resp = client.post("/api/auth/login", json={"email": email, "password": pwd})
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def user2_token(client, setup_test_suite_database):
    email = "user2@example.com"
    pwd = "User2Password123!"
    client.post("/api/auth/register", json={"name": "User Two", "email": email, "password": pwd, "confirm_password": pwd})
    
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    u = db.query(User).filter(User.email == email).first()
    if u:
        u.is_verified = True
        db.commit()
    db.close()
    
    resp = client.post("/api/auth/login", json={"email": email, "password": pwd})
    return resp.json()["access_token"]


def _create_real_wav_bytes(duration_sec=1.0, sample_rate=44100) -> bytes:
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, audio_data)
    buf.seek(0)
    return buf.read()


def _create_real_mp4_bytes(num_frames=10, width=64, height=64) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        temp_path = f.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, 10.0, (width, height))
        for i in range(num_frames):
            frame = np.full((height, width, 3), (i * 25) % 255, dtype=np.uint8)
            out.write(frame)
        out.release()

        with open(temp_path, "rb") as f:
            video_bytes = f.read()
        return video_bytes
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


class TestMultimodalUploads:
    def test_upload_image_synchronous_inference(self, client, user1_token):
        from PIL import Image
        img = Image.new("RGB", (64, 64), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

        resp = client.post(
            "/api/analysis/image",
            headers={"Authorization": f"Bearer {user1_token}"},
            files={"file": ("blue.jpg", image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 202
        analysis_id = resp.json()["analysis_id"]

        detail = client.get(
            f"/api/analysis/{analysis_id}",
            headers={"Authorization": f"Bearer {user1_token}"},
        ).json()
        assert detail["status"] in ("completed", "failed")
        assert detail["media_type"] == "image"

    def test_upload_video_queues_and_processes(self, client, user1_token):
        video_bytes = _create_real_mp4_bytes()
        resp = client.post(
            "/api/analysis/video",
            headers={"Authorization": f"Bearer {user1_token}"},
            files={"file": ("sample.mp4", video_bytes, "video/mp4")},
        )
        assert resp.status_code == 202
        analysis_id = resp.json()["analysis_id"]

        detail = client.get(
            f"/api/analysis/{analysis_id}",
            headers={"Authorization": f"Bearer {user1_token}"},
        ).json()
        assert detail["id"] == analysis_id
        assert detail["media_type"] == "video"

    def test_upload_audio_queues_and_processes(self, client, user1_token):
        wav_bytes = _create_real_wav_bytes()
        resp = client.post(
            "/api/analysis/audio",
            headers={"Authorization": f"Bearer {user1_token}"},
            files={"file": ("tone.wav", wav_bytes, "audio/wav")},
        )
        assert resp.status_code == 202
        analysis_id = resp.json()["analysis_id"]

        detail = client.get(
            f"/api/analysis/{analysis_id}",
            headers={"Authorization": f"Bearer {user1_token}"},
        ).json()
        assert detail["id"] == analysis_id
        assert detail["media_type"] == "audio"


class TestAccessControlAndIsolation:
    def test_user2_cannot_access_user1_analysis(self, client, user1_token, user2_token):
        from PIL import Image
        img = Image.new("RGB", (32, 32), color="green")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

        resp = client.post(
            "/api/analysis/image",
            headers={"Authorization": f"Bearer {user1_token}"},
            files={"file": ("private.jpg", image_bytes, "image/jpeg")},
        )
        analysis_id = resp.json()["analysis_id"]

        u2_resp = client.get(
            f"/api/analysis/{analysis_id}",
            headers={"Authorization": f"Bearer {user2_token}"},
        )
        assert u2_resp.status_code == 403

        u2_del = client.delete(
            f"/api/analysis/{analysis_id}",
            headers={"Authorization": f"Bearer {user2_token}"},
        )
        assert u2_del.status_code == 403
