import os
import pytest
from pathlib import Path
from PIL import Image
import numpy as np

from app.services.gradcam_service import (
    generate_image_gradcam,
    generate_video_gradcam_frames,
    HEATMAP_CACHE_DIR,
)

REAL_IMAGE = Path(__file__).parents[2] / "ai" / "evaluation" / "real" / "033.jpg"
FAKE_IMAGE = Path(__file__).parents[2] / "ai" / "evaluation" / "manipulated" / "066_062.jpg"
REAL_VIDEO = Path(__file__).parents[2] / "ai" / "evaluation" / "original_c23_subset" / "original_sequences" / "youtube" / "c23" / "videos" / "033.mp4"


def test_generate_image_gradcam_real():
    assert REAL_IMAGE.is_file(), f"Real image test file missing: {REAL_IMAGE}"
    overlay_out = str(HEATMAP_CACHE_DIR / "test_real_overlay.jpg")
    heatmap_out = str(HEATMAP_CACHE_DIR / "test_real_heatmap.jpg")

    meta = generate_image_gradcam(
        image_path=str(REAL_IMAGE),
        overlay_out_path=overlay_out,
        heatmap_out_path=heatmap_out,
    )

    assert meta["target_class"] in (0, 1)
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert 0.0 <= meta["cam_mean"] <= 1.0
    assert meta["cam_max"] > 0.0

    assert os.path.isfile(overlay_out)
    assert os.path.isfile(heatmap_out)

    img = Image.open(overlay_out)
    assert img.size == (meta["width"], meta["height"])
    arr = np.array(img)
    # Ensure image is not blank/uniform
    assert np.std(arr) > 1.0


def test_generate_image_gradcam_fake():
    assert FAKE_IMAGE.is_file(), f"Fake image test file missing: {FAKE_IMAGE}"
    overlay_out = str(HEATMAP_CACHE_DIR / "test_fake_overlay.jpg")

    meta = generate_image_gradcam(
        image_path=str(FAKE_IMAGE),
        overlay_out_path=overlay_out,
    )

    assert meta["target_class"] in (0, 1)
    assert meta["class_label"] in ("authentic", "synthetic")
    assert os.path.isfile(overlay_out)


def test_generate_video_gradcam_frames():
    assert REAL_VIDEO.is_file(), f"Video test file missing: {REAL_VIDEO}"

    frames = generate_video_gradcam_frames(
        video_path=str(REAL_VIDEO),
        analysis_id=9999,
        num_frames=5,
    )

    assert len(frames) == 5
    for f in frames:
        assert "frame_index" in f
        assert "timestamp_seconds" in f
        assert os.path.isfile(f["original_path"])
        assert os.path.isfile(f["heatmap_path"])
        img = Image.open(f["heatmap_path"])
        assert img.size[0] > 0 and img.size[1] > 0


@pytest.fixture(scope="module")
def auth_token(client, setup_test_suite_database):
    """Register and activate test user, return token."""
    from app.models.auth import User
    from conftest import TestingSessionLocal

    email = "testgradcam@example.com"
    password = "TestPassword123!"

    client.post("/api/auth/register", json={
        "name": "GradCAM User",
        "email": email,
        "password": password,
        "confirm_password": password,
    })

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_verified = True
        db.commit()
    db.close()

    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })
    return login_resp.json()["access_token"]


def test_heatmap_api_endpoints(client, auth_token):
    token_headers = {"Authorization": f"Bearer {auth_token}"}

    # 1. Upload an image
    with open(REAL_IMAGE, "rb") as f:
        resp = client.post(
            "/api/analysis/image",
            headers=token_headers,
            files={"file": ("033.jpg", f, "image/jpeg")},
        )
    assert resp.status_code == 202
    analysis_id = resp.json()["analysis_id"]

    # 2. Query analysis detail - verify heatmap availability metadata
    detail_resp = client.get(f"/api/analysis/{analysis_id}", headers=token_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["heatmap_available"] is True
    assert f"/api/analysis/{analysis_id}/heatmap" in detail["heatmap_url"]

    # 3. Query heatmap endpoint
    heat_resp = client.get(f"/api/analysis/{analysis_id}/heatmap", headers=token_headers)
    assert heat_resp.status_code == 200
    assert heat_resp.headers["content-type"] == "image/jpeg"
    assert len(heat_resp.content) > 1000

    # 4. Query original media endpoint
    media_resp = client.get(f"/api/analysis/{analysis_id}/media", headers=token_headers)
    assert media_resp.status_code == 200
    assert len(media_resp.content) > 1000

    # 5. Security: Unauthenticated request should fail with 401
    unauth_resp = client.get(f"/api/analysis/{analysis_id}/heatmap")
    assert unauth_resp.status_code == 401
