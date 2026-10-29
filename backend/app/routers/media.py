"""
Secure Media router for privately stored condition photos.
Enforces cryptographic HMAC-SHA256 signature verification and timestamp expiration against app_now().
"""
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.services.storage_service import get_photo_path, verify_signed_url

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/condition-photos/{filename}")
def get_condition_photo(
    filename: str,
    sig: str = Query(..., description="Cryptographic HMAC-SHA256 signature"),
    exp: int = Query(..., description="Expiration epoch timestamp"),
):
    """
    Serves a privately stored condition photo or advisory diff image.
    Strictly verifies that the signature matches and that app_now() <= exp.
    """
    if not verify_signed_url(filename, sig, exp):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or expired signed photo URL.",
        )

    path = get_photo_path(filename)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found.")

    return FileResponse(
        path=path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )

