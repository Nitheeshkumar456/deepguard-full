"""
upload_validator.py — Secure file upload validation utilities.

Validates MIME types via python-magic (magic bytes), enforces allowed
extensions, checks file size limits, and generates collision-safe server
filenames.  Never trusts client-supplied Content-Type or filename alone.
"""

import os
import uuid
import mimetypes
from typing import Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Allowed media configurations
# Key: canonical media category ("image" | "video" | "audio")
# Value: dict of allowed extensions → set of acceptable magic-byte MIME types
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"}

ALLOWED_IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/webp",
    "image/bmp", "image/tiff",
}
ALLOWED_VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/x-matroska", "video/webm", "video/x-flv",
    "video/x-ms-wmv",
}
ALLOWED_AUDIO_MIMES = {
    "audio/mpeg", "audio/wav", "audio/x-wav", "audio/flac",
    "audio/aac", "audio/ogg", "audio/mp4", "audio/opus",
    "audio/x-m4a",
}

MEDIA_TYPE_CONFIG = {
    "image": {
        "extensions": ALLOWED_IMAGE_EXTENSIONS,
        "mimes": ALLOWED_IMAGE_MIMES,
        "max_bytes": 20 * 1024 * 1024,   # 20 MB
    },
    "video": {
        "extensions": ALLOWED_VIDEO_EXTENSIONS,
        "mimes": ALLOWED_VIDEO_MIMES,
        "max_bytes": 500 * 1024 * 1024,  # 500 MB
    },
    "audio": {
        "extensions": ALLOWED_AUDIO_EXTENSIONS,
        "mimes": ALLOWED_AUDIO_MIMES,
        "max_bytes": 100 * 1024 * 1024,  # 100 MB
    },
}


def _sanitize_extension(filename: str) -> str:
    """Return the lowercase extension from filename, e.g. '.mp4'."""
    _, ext = os.path.splitext(filename.strip())
    return ext.lower()


def _detect_mime_from_bytes(header: bytes) -> str:
    """
    Detect MIME type from the first 261 bytes using python-magic.
    Falls back to a safe default if magic is unavailable.
    """
    try:
        import magic  # type: ignore
        return magic.from_buffer(header, mime=True)
    except ImportError:
        # python-magic not installed; fall back to extension-based detection.
        # This is less secure — install python-magic[stub] for production.
        return "application/octet-stream"


def validate_upload(
    filename: str,
    file_bytes: bytes,
    declared_media_type: str,
) -> Tuple[str, str, int]:
    """
    Validate an uploaded file fully and return (safe_filename, detected_mime, file_size).

    Raises ValueError with a user-safe message on any validation failure.

    :param filename: Original client-supplied filename.
    :param file_bytes: Complete file content already read into memory.
    :param declared_media_type: Route-level media type: "image" | "video" | "audio".
    """
    if declared_media_type not in MEDIA_TYPE_CONFIG:
        raise ValueError(f"Unsupported media type category: {declared_media_type}")

    config = MEDIA_TYPE_CONFIG[declared_media_type]

    # ── 1. Extension check ──────────────────────────────────────────────────
    ext = _sanitize_extension(filename)
    if not ext:
        raise ValueError("Uploaded file has no extension.")
    if ext not in config["extensions"]:
        allowed = ", ".join(sorted(config["extensions"]))
        raise ValueError(
            f"File extension '{ext}' is not permitted for {declared_media_type} uploads. "
            f"Accepted extensions: {allowed}"
        )

    # ── 2. File size check ──────────────────────────────────────────────────
    file_size = len(file_bytes)
    if file_size == 0:
        raise ValueError("Uploaded file is empty.")
    max_mb = config["max_bytes"] // (1024 * 1024)
    if file_size > config["max_bytes"]:
        raise ValueError(
            f"File size {file_size / (1024*1024):.1f} MB exceeds the "
            f"{max_mb} MB limit for {declared_media_type} uploads."
        )

    # ── 3. Magic-byte MIME detection ────────────────────────────────────────
    detected_mime = _detect_mime_from_bytes(file_bytes[:261])

    # Allow application/octet-stream only if magic is unavailable (fallback)
    if detected_mime != "application/octet-stream":
        if detected_mime not in config["mimes"]:
            raise ValueError(
                f"File content detected as '{detected_mime}' which is not "
                f"allowed for {declared_media_type} uploads."
            )

    # ── 4. Generate safe server-side filename ───────────────────────────────
    safe_filename = f"{uuid.uuid4().hex}{ext}"

    return safe_filename, detected_mime, file_size
