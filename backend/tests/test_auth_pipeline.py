"""
test_auth_pipeline.py — Comprehensive tests for authentication, authorization, OTP, and password reset flows.
"""

import pytest
from app.models.auth import User, OTP, PasswordResetToken


class TestRegistration:
    def test_register_short_password_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Weak User",
            "email": "weak@example.com",
            "password": "123",
            "confirm_password": "123"
        })
        assert resp.status_code == 422

    def test_register_weak_password_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Weak User",
            "email": "weak2@example.com",
            "password": "lowercasepasswordonly",
            "confirm_password": "lowercasepasswordonly"
        })
        assert resp.status_code == 400
        assert "uppercase" in resp.json()["detail"].lower() or "digit" in resp.json()["detail"].lower()

    def test_register_success_creates_otp_and_unverified_user(self, client, db_session):
        resp = client.post("/api/auth/register", json={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        })
        assert resp.status_code == 201
        assert "Registration successful" in resp.json()["message"]

        user = db_session.query(User).filter(User.email == "alice@example.com").first()
        assert user is not None
        assert user.is_verified is False
        
        otp = db_session.query(OTP).filter(OTP.email == "alice@example.com", OTP.purpose == "register").first()
        assert otp is not None
        assert len(otp.code) == 6

    def test_duplicate_registration_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Alice Duplicate",
            "email": "alice@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        })
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]


class TestLoginAndOTPVerification:
    def test_login_unverified_user_returns_403(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "alice@example.com",
            "password": "StrongPassword123!"
        })
        assert resp.status_code == 403
        assert "not been verified" in resp.json()["detail"]

    def test_verify_otp_invalid_code(self, client):
        resp = client.post("/api/auth/verify-otp", json={
            "email": "alice@example.com",
            "code": "000000",
            "purpose": "register"
        })
        assert resp.status_code == 400
        assert "Invalid or expired" in resp.json()["detail"]

    def test_verify_otp_success_activates_user(self, client, db_session):
        otp = db_session.query(OTP).filter(OTP.email == "alice@example.com", OTP.purpose == "register").order_by(OTP.id.desc()).first()
        valid_code = otp.code

        resp = client.post("/api/auth/verify-otp", json={
            "email": "alice@example.com",
            "code": valid_code,
            "purpose": "register"
        })
        assert resp.status_code == 200
        assert resp.json()["verified"] is True

        user = db_session.query(User).filter(User.email == "alice@example.com").first()
        assert user.is_verified is True

    def test_login_verified_user_success(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "alice@example.com",
            "password": "StrongPassword123!"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_rejected(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "alice@example.com",
            "password": "WrongPassword123!"
        })
        assert resp.status_code == 401

    def test_get_current_user_profile(self, client):
        login_resp = client.post("/api/auth/login", json={
            "email": "alice@example.com",
            "password": "StrongPassword123!"
        })
        token = login_resp.json()["access_token"]

        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        user_info = me_resp.json()
        assert user_info["email"] == "alice@example.com"
        assert user_info["name"] == "Alice Smith"
        assert user_info["is_verified"] is True


class TestPasswordResetFlow:
    def test_forgot_password_generates_reset_otp(self, client, db_session):
        resp = client.post("/api/auth/forgot-password", json={
            "email": "alice@example.com"
        })
        assert resp.status_code == 200

        otp = db_session.query(OTP).filter(OTP.email == "alice@example.com", OTP.purpose == "reset").first()
        assert otp is not None

    def test_verify_reset_otp_returns_reset_token(self, client, db_session):
        otp = db_session.query(OTP).filter(OTP.email == "alice@example.com", OTP.purpose == "reset", OTP.verified == False).order_by(OTP.id.desc()).first()
        assert otp is not None
        code = otp.code

        resp = client.post("/api/auth/verify-otp", json={
            "email": "alice@example.com",
            "code": code,
            "purpose": "reset"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert data.get("reset_token") is not None

        # Reset password using token
        reset_token = data["reset_token"]
        new_password = "BrandNewPassword123!"
        reset_resp = client.post("/api/auth/reset-password", json={
            "email": "alice@example.com",
            "token": reset_token,
            "new_password": new_password
        })
        assert reset_resp.status_code == 200

        # Verify login works with new password
        login_resp = client.post("/api/auth/login", json={
            "email": "alice@example.com",
            "password": new_password
        })
        assert login_resp.status_code == 200


class TestEmailServiceAndDelivery:
    def test_send_otp_email_success_starttls(self, monkeypatch):
        from unittest.mock import MagicMock
        from app.services.email_service import send_otp_email

        mock_smtp = MagicMock()
        monkeypatch.setattr("smtplib.SMTP", MagicMock(return_value=mock_smtp))
        mock_smtp.__enter__.return_value = mock_smtp

        result = send_otp_email(
            recipient_email="test@example.com",
            otp_code="123456",
            purpose="register",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="abcd efgh ijkl mnop",  # Contains spaces
            sender_name="DeepGuard AI"
        )
        assert result is True
        mock_smtp.starttls.assert_called_once()
        # Ensure spaces were stripped in login call
        mock_smtp.login.assert_called_once_with("sender@gmail.com", "abcdefghijklmnop")
        mock_smtp.sendmail.assert_called_once()

    def test_send_otp_email_success_ssl(self, monkeypatch):
        from unittest.mock import MagicMock
        from app.services.email_service import send_otp_email

        mock_smtp_ssl = MagicMock()
        monkeypatch.setattr("smtplib.SMTP_SSL", MagicMock(return_value=mock_smtp_ssl))
        mock_smtp_ssl.__enter__.return_value = mock_smtp_ssl

        result = send_otp_email(
            recipient_email="test@example.com",
            otp_code="654321",
            purpose="reset",
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_user="sender@gmail.com",
            smtp_password="secretpassword",
            sender_name="DeepGuard AI"
        )
        assert result is True
        mock_smtp_ssl.login.assert_called_once_with("sender@gmail.com", "secretpassword")
        mock_smtp_ssl.sendmail.assert_called_once()

    def test_registration_failure_when_smtp_fails(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "SMTP_USER", "sender@gmail.com")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "apppassword")
        monkeypatch.setattr("app.routes.auth.send_otp_email", lambda **kwargs: False)

        resp = client.post("/api/auth/register", json={
            "name": "Failed Delivery",
            "email": "fail@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        })
        assert resp.status_code == 500
        assert "Unable to send OTP email" in resp.json()["detail"]

    def test_resend_otp_failure_when_smtp_fails(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "SMTP_USER", "sender@gmail.com")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "apppassword")
        monkeypatch.setattr("app.routes.auth.send_otp_email", lambda **kwargs: False)

        resp = client.post("/api/auth/send-otp", json={
            "email": "alice@example.com"
        })
        assert resp.status_code == 500
        assert "Unable to send OTP email" in resp.json()["detail"]

    def test_forgot_password_failure_when_smtp_fails(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "SMTP_USER", "sender@gmail.com")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "apppassword")
        monkeypatch.setattr("app.routes.auth.send_otp_email", lambda **kwargs: False)

        resp = client.post("/api/auth/forgot-password", json={
            "email": "alice@example.com"
        })
        assert resp.status_code == 500
        assert "Unable to send OTP email" in resp.json()["detail"]

