"""
FastAPI dependency functions for authentication and role-based access control.
"""
from __future__ import annotations

import os
from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db

SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Decode JWT and return the active User ORM object."""
    # Import here to avoid circular imports
    from app.models import User  # noqa: PLC0415

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    """Return a FastAPI dependency that enforces one of the given roles."""
    def _check(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role(s): {', '.join(roles)}. Your role: {current_user.role}.",
            )
        return current_user
    return _check


# ── Convenience dependencies ───────────────────────────────────────────────────

def get_admin(user=Depends(require_roles("admin"))):
    return user


def get_manager_or_admin(user=Depends(require_roles("manager", "admin"))):
    return user


def get_owner_or_above(user=Depends(require_roles("owner", "manager", "admin"))):
    return user


def get_any_authenticated(user=Depends(get_current_user)):
    return user


def is_demo_mode() -> bool:
    """Check if DEMO_MODE is active (defaults to True for demo/hackathon environments)."""
    return os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")


def require_demo_mode():
    """Dependency that blocks demo endpoints if DEMO_MODE is explicitly disabled."""
    if not is_demo_mode():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DEMO_MODE is disabled in this environment. Demo logins, database resets, and synthetic clock controls are blocked.",
        )


