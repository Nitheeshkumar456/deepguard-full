"""
email_service.py — SMTP email delivery service for OTP and password reset emails.

Uses Python stdlib smtplib with Gmail STARTTLS (port 587).
Credentials are loaded from environment variables via Settings.
Falls back to console stub log when SMTP is not configured.
"""

import smtplib
import socket
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

logger = logging.getLogger(__name__)


def _build_otp_html(otp_code: str, purpose: str, recipient_email: str) -> str:
    """Render an HTML email body for an OTP delivery."""
    if purpose == "register":
        subject_text = "Verify your DeepGuard AI account"
        action_text = "verify your email address and activate your account"
    else:
        subject_text = "DeepGuard AI — Password Reset Code"
        action_text = "reset your password"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{subject_text}</title>
</head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Inter,Segoe UI,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:16px;padding:40px 36px;border:1px solid rgba(255,255,255,0.08);">
          <tr>
            <td align="center" style="padding-bottom:28px;">
              <div style="display:inline-flex;align-items:center;gap:10px;">
                <div style="background:#7c3aed;border-radius:10px;width:40px;height:40px;display:inline-block;text-align:center;line-height:40px;font-size:20px;">🛡️</div>
                <span style="color:#ffffff;font-weight:700;font-size:18px;vertical-align:middle;">DeepGuard AI</span>
              </div>
            </td>
          </tr>
          <tr>
            <td style="color:#f1f5f9;font-size:22px;font-weight:700;text-align:center;padding-bottom:12px;">
              Your Verification Code
            </td>
          </tr>
          <tr>
            <td style="color:#94a3b8;font-size:14px;text-align:center;padding-bottom:32px;line-height:1.6;">
              Use the following 6-digit code to {action_text}.<br/>
              This code expires in <strong style="color:#e2e8f0;">10 minutes</strong>.
            </td>
          </tr>
          <tr>
            <td align="center" style="padding-bottom:32px;">
              <div style="background:#0f172a;border:2px solid #7c3aed;border-radius:12px;padding:20px 40px;display:inline-block;">
                <span style="font-size:36px;font-weight:800;letter-spacing:12px;color:#ffffff;font-family:monospace;">{otp_code}</span>
              </div>
            </td>
          </tr>
          <tr>
            <td style="color:#64748b;font-size:12px;text-align:center;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);">
              If you did not request this code, please ignore this email.<br/>
              This is an automated message — please do not reply.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def send_otp_email(
    recipient_email: str,
    otp_code: str,
    purpose: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sender_name: str = "DeepGuard AI",
) -> bool:
    """
    Send an OTP email via SMTP (STARTTLS port 587 or direct SSL port 465).

    Returns True on successful delivery, False on any failure.
    Logs errors safely without leaking credentials.
    """
    clean_user = smtp_user.strip().strip("'\"")
    # Clean spaces (e.g. from Google 16-character App Passwords 'xxxx xxxx xxxx xxxx')
    clean_password = smtp_password.replace(" ", "").strip().strip("'\"")
    clean_recipient = recipient_email.strip()

    if not clean_user or not clean_password:
        logger.error("Cannot send email: SMTP username or password is missing.")
        return False

    if purpose == "register":
        subject = "DeepGuard AI — Email Verification Code"
    else:
        subject = "DeepGuard AI — Password Reset Code"

    html_body = _build_otp_html(otp_code, purpose, clean_recipient)
    plain_body = (
        f"Your DeepGuard AI verification code is: {otp_code}\n\n"
        f"This code expires in 10 minutes.\n"
        f"If you did not request this, please ignore this email."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, clean_user))
    msg["To"] = clean_recipient

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if int(smtp_port) == 465:
            # Direct SSL / SMTPS connection (e.g. port 465)
            with smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=15) as server:
                server.login(clean_user, clean_password)
                server.sendmail(clean_user, [clean_recipient], msg.as_string())
        else:
            # STARTTLS connection (e.g. Gmail port 587, custom port 25/2525)
            with smtplib.SMTP(smtp_host, int(smtp_port), timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(clean_user, clean_password)
                server.sendmail(clean_user, [clean_recipient], msg.as_string())
        logger.info(f"OTP email successfully dispatched to {clean_recipient} (purpose={purpose})")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. For Gmail, ensure you are using a 16-character App Password "
            "(not your standard Google account password). "
            "Enable 2-Step Verification and generate an App Password at: https://myaccount.google.com/apppasswords"
        )
        return False
    except smtplib.SMTPConnectError as exc:
        logger.error(f"SMTP connection error to {smtp_host}:{smtp_port}: {exc}")
        return False
    except smtplib.SMTPException as exc:
        logger.error(f"SMTP protocol error sending OTP to {clean_recipient}: {exc}")
        return False
    except (socket.error, socket.timeout, TimeoutError, OSError) as exc:
        logger.error(f"Network error connecting to SMTP server {smtp_host}:{smtp_port}: {exc}")
        return False
    except Exception as exc:
        logger.error(f"Unexpected error sending OTP email: {exc}")
        return False
