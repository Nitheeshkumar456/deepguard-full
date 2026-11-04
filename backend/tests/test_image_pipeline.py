"""
test_image_pipeline.py — End-to-end tests for the image analysis pipeline.
"""

import io
import os
import pytest
from app.models.auth import User


@pytest.fixture(scope="module")
def auth_token(client, setup_test_suite_database):
    """Register and activate test user, return token."""
    email = "testpipeline@example.com"
    password = "TestPassword123!"
    
    # Register
    client.post("/api/auth/register", json={
        "name": "Test User",
        "email": email,
        "password": password,
        "confirm_password": password,
    })

    # Query directly from test DB and mark verified
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_verified = True
        db.commit()
    db.close()

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })
    return login_resp.json()["access_token"]


def _create_test_image(width=100, height=100, color=(255, 0, 0), fmt="JPEG") -> bytes:
    from PIL import Image
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestHealthCheck:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_status_endpoint(self, client):
        resp = client.get("/api/v1/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_ai_status_endpoint(self, client):
        resp = client.get("/api/v1/ai/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "loaded" in data
        assert "model_name" in data


class TestImageAnalysisPipeline:
    def test_upload_valid_jpeg(self, client, auth_token):
        image_bytes = _create_test_image(fmt="JPEG")

        resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("test_photo.jpg", image_bytes, "image/jpeg")},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert "analysis_id" in data
        assert data["media_type"] == "image"

        detail_resp = client.get(
            f"/api/analysis/{data['analysis_id']}",
            headers=_auth_headers(auth_token),
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] in ("completed", "failed")
        if detail["status"] == "completed":
            assert detail["result"] is not None
            assert 0.0 <= detail["result"]["confidence"] <= 1.0

    def test_upload_valid_png(self, client, auth_token):
        image_bytes = _create_test_image(fmt="PNG")

        resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("test_image.png", image_bytes, "image/png")},
        )
        assert resp.status_code == 202
        data = resp.json()

        detail_resp = client.get(
            f"/api/analysis/{data['analysis_id']}",
            headers=_auth_headers(auth_token),
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] in ("completed", "failed")

    def test_confidence_not_random(self, client, auth_token):
        image_bytes = _create_test_image(width=50, height=50, color=(0, 128, 255))

        results = []
        for _ in range(2):
            resp = client.post(
                "/api/analysis/image",
                headers=_auth_headers(auth_token),
                files={"file": ("determinism_test.jpg", image_bytes, "image/jpeg")},
            )
            assert resp.status_code == 202
            data = resp.json()
            detail = client.get(
                f"/api/analysis/{data['analysis_id']}",
                headers=_auth_headers(auth_token),
            ).json()
            if detail["status"] == "completed" and detail.get("result"):
                results.append(detail["result"]["confidence"])

        if len(results) == 2:
            assert results[0] == results[1]


class TestErrorHandling:
    def test_upload_empty_file(self, client, auth_token):
        resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 422

    def test_upload_unsupported_extension(self, client, auth_token):
        resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("document.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
        )
        assert resp.status_code == 422

    def test_upload_text_as_image(self, client, auth_token):
        resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("fake.jpg", b"This is just text, not an image", "image/jpeg")},
        )
        assert resp.status_code in (202, 422)
        if resp.status_code == 202:
            data = resp.json()
            detail = client.get(
                f"/api/analysis/{data['analysis_id']}",
                headers=_auth_headers(auth_token),
            ).json()
            assert detail["status"] == "failed"

    def test_upload_without_auth(self, client):
        image_bytes = _create_test_image()
        resp = client.post(
            "/api/analysis/image",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 401

    def test_upload_no_file(self, client, auth_token):
        resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
        )
        assert resp.status_code == 422


class TestRetrievalEndpoints:
    def test_get_history(self, client, auth_token):
        resp = client.get(
            "/api/analysis/history",
            headers=_auth_headers(auth_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_get_analysis_detail(self, client, auth_token):
        image_bytes = _create_test_image()
        upload_resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("detail_test.jpg", image_bytes, "image/jpeg")},
        )
        analysis_id = upload_resp.json()["analysis_id"]

        detail_resp = client.get(
            f"/api/analysis/{analysis_id}",
            headers=_auth_headers(auth_token),
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == analysis_id

    def test_get_nonexistent_analysis(self, client, auth_token):
        resp = client.get(
            "/api/analysis/99999",
            headers=_auth_headers(auth_token),
        )
        assert resp.status_code == 404

    def test_delete_analysis(self, client, auth_token):
        image_bytes = _create_test_image()
        upload_resp = client.post(
            "/api/analysis/image",
            headers=_auth_headers(auth_token),
            files={"file": ("delete_test.jpg", image_bytes, "image/jpeg")},
        )
        analysis_id = upload_resp.json()["analysis_id"]

        delete_resp = client.delete(
            f"/api/analysis/{analysis_id}",
            headers=_auth_headers(auth_token),
        )
        assert delete_resp.status_code == 200

        get_resp = client.get(
            f"/api/analysis/{analysis_id}",
            headers=_auth_headers(auth_token),
        )
        assert get_resp.status_code == 404

    def test_history_filter_by_media_type(self, client, auth_token):
        resp = client.get(
            "/api/analysis/history?media_type=image",
            headers=_auth_headers(auth_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["media_type"] == "image"

    def test_history_filter_by_status(self, client, auth_token):
        resp = client.get(
            "/api/analysis/history?status=completed",
            headers=_auth_headers(auth_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "completed"
