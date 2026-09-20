"""Mailgun delivery service for privacy-minimal visitor alert notifications."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

from backend.app.core.config import settings

logger = logging.getLogger("cryos.mailgun")


def format_duration(seconds: float) -> str:
    """Format duration in seconds into 'approximately Xm Ys' or 'approximately Xs'."""
    sec = max(0, int(round(seconds)))
    if sec < 60:
        return f"approximately {sec}s"
    minutes = sec // 60
    rem_sec = sec % 60
    if rem_sec == 0:
        return f"approximately {minutes}m"
    return f"approximately {minutes}m {rem_sec}s"


def format_ist_timestamp(dt: datetime) -> str:
    """Convert UTC datetime to IST formatted string, e.g. '10:42 PM IST'."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ist_dt = dt.astimezone(ist_tz)
    hour_12 = ist_dt.strftime("%I").lstrip("0") or "12"
    minute = ist_dt.strftime("%M")
    ampm = ist_dt.strftime("%p")
    return f"{hour_12}:{minute} {ampm} IST"


def generate_email_text(
    duration_seconds: float,
    page_count: int,
    first_page: str,
    last_page: str,
    started_at: datetime,
) -> str:
    """Generate compact, privacy-honest email body for the owner alert."""
    duration_str = format_duration(duration_seconds)
    started_str = format_ist_timestamp(started_at)

    return (
        "CRYOS visitor detected\n\n"
        f"Session duration: {duration_str}\n"
        f"Pages viewed: {page_count}\n"
        f"First page: {first_page}\n"
        f"Last page: {last_page}\n"
        f"Session started: {started_str}\n\n"
        "No visitor identity information was collected."
    )


async def send_visitor_alert_email(
    duration_seconds: float,
    page_count: int,
    first_page: str,
    last_page: str,
    started_at: datetime,
) -> bool:
    """Send an operational visitor alert email to the configured owner address via Mailgun.

    Fails silently on network, credential, or API errors, returning False without raising.
    Never logs credentials or authorization headers.
    """
    api_key = settings.MAILGUN_API_KEY
    domain = settings.MAILGUN_DOMAIN
    recipient = settings.MAILGUN_RECIPIENT_EMAIL
    sender = settings.MAILGUN_FROM
    base_url = settings.MAILGUN_API_URL

    if not api_key or not recipient or not domain:
        logger.info(
            "Mailgun alert skipped: MAILGUN_API_KEY, MAILGUN_DOMAIN, or MAILGUN_RECIPIENT_EMAIL not configured."
        )
        return False

    url = f"{base_url.rstrip('/')}/{domain}/messages"
    subject = "CRYOS visitor detected"
    text_content = generate_email_text(
        duration_seconds=duration_seconds,
        page_count=page_count,
        first_page=first_page,
        last_page=last_page,
        started_at=started_at,
    )

    data = {
        "from": sender,
        "to": recipient,
        "subject": subject,
        "text": text_content,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                auth=("api", api_key),
                data=data,
            )

        if response.status_code >= 200 and response.status_code < 300:
            logger.info("Visitor alert email delivered to Mailgun successfully.")
            return True
        else:
            logger.warning(
                "Mailgun rejected visitor alert email: HTTP status %s",
                response.status_code,
            )
            return False
    except httpx.TimeoutException:
        logger.warning("Mailgun request timed out when sending visitor alert.")
        return False
    except httpx.RequestError as exc:
        logger.warning("Mailgun network request error: %s", type(exc).__name__)
        return False
    except Exception as exc:
        logger.warning("Unexpected error during Mailgun delivery: %s", type(exc).__name__)
        return False
