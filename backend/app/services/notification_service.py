"""
Notification service — creates in-app Notification rows.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import Notification
from app.clock import app_now


def notify(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notif_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notif_type=notif_type,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
        created_at=app_now(),
    )
    db.add(n)
    db.flush()
    return n

