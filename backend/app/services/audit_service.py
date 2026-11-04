import logging
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from ..models.security import SecurityAuditLog

logger = logging.getLogger(__name__)

def extract_device_info(request: Optional[Request]):
    """Extract client IP, platform, and friendly device description from HTTP request."""
    if not request:
        return {
            "ip_address": "127.0.0.1",
            "user_agent": "Unknown",
            "platform": "Unknown",
            "device_name": "Generic Device"
        }

    ip = request.headers.get("x-forwarded-for")
    if ip:
        ip = ip.split(",")[0].strip()
    elif request.client and request.client.host:
        ip = request.client.host
    else:
        ip = "127.0.0.1"

    ua = request.headers.get("user-agent", "Unknown")

    if "Android" in ua:
        platform = "Android"
        device_name = "Android Mobile"
    elif "iPhone" in ua or "iPad" in ua:
        platform = "iOS"
        device_name = "Apple iOS Device"
    elif "Windows" in ua:
        platform = "Windows"
        device_name = "Windows PC"
    elif "Macintosh" in ua or "Mac OS" in ua:
        platform = "macOS"
        device_name = "Mac"
    elif "Linux" in ua:
        platform = "Linux"
        device_name = "Linux Workstation"
    else:
        platform = "Web"
        device_name = "Web Client"

    return {
        "ip_address": ip,
        "user_agent": ua[:250],
        "platform": platform,
        "device_name": device_name
    }

def log_security_event(
    db: Session,
    user_id: int,
    action: str,
    status: str = "SUCCESS",
    details: Optional[str] = None,
    request: Optional[Request] = None
) -> Optional[SecurityAuditLog]:
    """Persist a security and governance audit event safely."""
    try:
        dev = extract_device_info(request)
        entry = SecurityAuditLog(
            user_id=user_id,
            action=action,
            status=status,
            ip_address=dev["ip_address"],
            user_agent=dev["user_agent"],
            details=details,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as exc:
        logger.warning(f"Failed to record audit log: {exc}")
        return None
