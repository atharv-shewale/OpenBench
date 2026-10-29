"""
Private storage service for OpenBench condition photos.
Photos are stored privately (outside public web directories) and served only via signed URLs
with cryptographic HMAC-SHA256 signatures and timestamp-based expiration verified against app_now().
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Optional

from app.clock import app_now
from app.dependencies import SECRET_KEY

# Root directory for private photo storage
PRIVATE_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "private_storage" / "condition_photos"
PRIVATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_photo_bytes(data: bytes, prefix: str = "cond") -> str:
    """
    Saves raw image bytes to the private storage directory with a secure unique filename.
    Returns the generated filename.
    """
    unique_id = uuid.uuid4().hex[:16]
    filename = f"{prefix}_{unique_id}.jpg"
    dest_path = PRIVATE_STORAGE_DIR / filename
    with open(dest_path, "wb") as f:
        f.write(data)
    return filename


def get_photo_path(filename: str) -> Optional[Path]:
    """
    Safely resolves a filename within PRIVATE_STORAGE_DIR, preventing path traversal.
    Returns Path if exists, or None.
    """
    clean_name = os.path.basename(filename)
    path = PRIVATE_STORAGE_DIR / clean_name
    if path.is_file():
        return path
    return None


def generate_signed_url(filename: str, expires_in_seconds: int = 7200) -> str:
    """
    Generates a cryptographically signed URL with expiration timestamp based on app_now().
    URL format: /api/media/condition-photos/{filename}?sig={sig}&exp={exp}
    """
    clean_name = os.path.basename(filename)
    now = app_now()
    exp = int((now + timedelta(seconds=expires_in_seconds)).timestamp())
    message = f"{clean_name}:{exp}".encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()[:32]
    return f"/api/media/condition-photos/{clean_name}?sig={sig}&exp={exp}"


def verify_signed_url(filename: str, sig: str, exp: int) -> bool:
    """
    Verifies that a signed URL is authentic, un-tampered, and not expired using app_now().
    """
    clean_name = os.path.basename(filename)
    now = app_now()
    if int(now.timestamp()) > exp:
        return False  # Expired

    message = f"{clean_name}:{exp}".encode("utf-8")
    expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(sig, expected_sig)

