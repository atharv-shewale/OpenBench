"""
Notification service — creates in-app Notification rows and handles simulated/SMTP email dispatch.
Supports all notification events:
- APPROVAL
- REJECTION
- WAITLIST_MOVE
- CANCELLATION
- EXTENSION
- REMINDER
- OVERDUE_RETURN
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Notification, User
from app.clock import app_now

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    action_type: str,
) -> bool:
    """
    Dispatches or logs an email notification to the user.
    In demo / testing / development mode, logs the full email message payload.
    Can be connected to SMTP / SendGrid / Postmark in production via env vars.
    """
    logger.info(
        "[EMAIL DISPATCH] To: %s | Subject: %s | Type: %s | Body: %s",
        to_email,
        subject,
        action_type,
        body,
    )
    return True


def notify(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notif_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    dispatch_email: bool = True,
) -> Notification:
    """
    Creates an in-app Notification and optionally sends a correlated email.
    """
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

    if dispatch_email:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.email:
            send_email(
                to_email=user.email,
                subject=f"[OpenBench] {title}",
                body=f"Hello {user.full_name},\n\n{message}\n\n— OpenBench Automated Lab Governance",
                action_type=notif_type,
            )

    return n
