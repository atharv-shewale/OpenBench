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
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
    Dispatches an email notification.
    If SMTP credentials (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
    are provided in environment, attempts delivery via SMTP.
    Otherwise, falls back to structured logging (simulated delivery) for hackathon demo & audit.
    """
    smtp_host = os.getenv("SMTP_HOST")
    if smtp_host:
        try:
            port = int(os.getenv("SMTP_PORT", "587"))
            user = os.getenv("SMTP_USER", "")
            password = os.getenv("SMTP_PASSWORD", "")
            sender = os.getenv("EMAIL_FROM", "notifications@openbench.in")

            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, port, timeout=5) as server:
                if os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"):
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
            logger.info("[EMAIL SENT via SMTP] To: %s | Subject: %s | Action: %s", to_email, subject, action_type)
            return True
        except Exception as exc:
            logger.warning("[EMAIL SMTP FAILED - FALLBACK TO SIMULATED LOG] %s", exc)

    logger.info(
        "[EMAIL SIMULATED / AUDIT DISPATCH] To: %s | Subject: %s | Type: %s | Body: %s",
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
