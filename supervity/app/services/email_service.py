# app/services/email_service.py
"""
Email service: SMTP sending, IMAP/Outlook listener, and persistent email storage.
"""

import email as email_lib
import imaplib
import logging
import os
import re
import smtplib
import threading
from datetime import datetime, timezone
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

from ..core.database import SessionLocal

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


def _smtp_config() -> dict:
    return {
        "server": _env("OUTLOOK_SMTP_SERVER", "smtp.office365.com"),
        "port": int(_env("OUTLOOK_SMTP_PORT", "587")),
        "user": _env("OUTLOOK_SMTP_USER", _env("OUTLOOK_EMAIL")),
        "password": _env("OUTLOOK_SMTP_PASSWORD", _env("OUTLOOK_API_KEY")),
        "sender": _env("OUTLOOK_SENDER", _env("OUTLOOK_SMTP_USER", _env("OUTLOOK_EMAIL", "supervity@example.com"))),
    }


def _imap_config() -> dict:
    return {
        "server": _env("OUTLOOK_IMAP_SERVER", "outlook.office365.com"),
        "user": _env("OUTLOOK_IMAP_USER", _env("OUTLOOK_EMAIL")),
        "password": _env("OUTLOOK_IMAP_PASSWORD", _env("OUTLOOK_PASSWORD")),
    }


def _email_enabled() -> bool:
    cfg = _smtp_config()
    return bool(cfg["user"] and cfg["password"])


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_db() -> Session:
    return SessionLocal()


def _store_email(
    direction: str,
    to_email: Optional[str],
    from_email: Optional[str],
    subject: Optional[str],
    body: Optional[str],
    status: str,
    source: str = "outlook",
    contact_id: Optional[str] = None,
    provider_message_id: Optional[str] = None,
    sent_at: Optional[datetime] = None,
    received_at: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> int:
    """Persist an email to the email_log table. Returns the new row id."""
    try:
        # Lazy import to avoid circular import during model registration
        from ..models.email import EmailLog

        db = _get_db()
        preview = (body or "")[:500]
        record = EmailLog(
            contact_id=contact_id,
            direction=direction,
            to_email=to_email,
            from_email=from_email,
            subject=subject,
            body=body,
            body_preview=preview,
            status=status,
            source=source,
            provider_message_id=provider_message_id,
            sent_at=sent_at,
            received_at=received_at,
            extra_metadata=metadata or {},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        db.close()
        log.info(f"Stored email_log row {record.id} ({direction}/{status}).")
        return record.id
    except Exception as e:
        log.error(f"Failed to store email: {e}")
        return -1


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------


def send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    reply_to: Optional[str] = None,
    contact_id: Optional[str] = None,
    source: str = "manual",
) -> bool:
    """
    Send an email via Outlook SMTP and persist it in email_log.
    If credentials are not configured, the email is still stored as 'queued'
    so the app never loses the record.
    """
    cfg = _smtp_config()

    # Always store the attempt first
    _store_email(
        direction="sent",
        to_email=to,
        from_email=cfg["sender"],
        subject=subject,
        body=body,
        status="queued",
        source=source,
        contact_id=contact_id,
        sent_at=datetime.now(timezone.utc),
        metadata={"cc": cc, "bcc": bcc, "reply_to": reply_to},
    )

    if not _email_enabled():
        log.warning("Outlook SMTP credentials not set; email stored as queued but not delivered.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["sender"]
        msg["To"] = to

        if cc:
            msg["Cc"] = cc
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body, "plain"))

        recipients = [to]
        if cc:
            recipients.extend([e.strip() for e in cc.split(",") if e.strip()])
        if bcc:
            recipients.extend([e.strip() for e in bcc.split(",") if e.strip()])

        with smtplib.SMTP(cfg["server"], cfg["port"], timeout=20) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            response = server.sendmail(cfg["sender"], recipients, msg.as_string())
            if response:
                log.warning(f"SMTP partial failure: {response}")

        _store_email(
            direction="sent",
            to_email=to,
            from_email=cfg["sender"],
            subject=subject,
            body=body,
            status="sent",
            source=source,
            contact_id=contact_id,
            sent_at=datetime.now(timezone.utc),
            metadata={"cc": cc, "bcc": bcc, "reply_to": reply_to, "smtp_response": str(response)},
        )
        log.info(f"Email sent to {to}: {subject}")
        return True

    except Exception as e:
        log.error(f"SMTP send failed: {e}")
        _store_email(
            direction="sent",
            to_email=to,
            from_email=cfg["sender"],
            subject=subject,
            body=body,
            status="failed",
            source=source,
            contact_id=contact_id,
            sent_at=datetime.now(timezone.utc),
            metadata={"cc": cc, "bcc": bcc, "reply_to": reply_to, "error": str(e)},
        )
        return False


# ---------------------------------------------------------------------------
# Outlook auto listener (IMAP)
# ---------------------------------------------------------------------------


def _decode_header_value(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded += part.decode(charset or "utf-8", errors="ignore")
        else:
            decoded += part
    return decoded


def _extract_plain_body(msg: email_lib.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="ignore")
                        break
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="ignore")
        except Exception:
            pass
    return re.sub(r"\r\n", "\n", body).strip()


def _match_contact_by_email(email_addr: str) -> Optional[str]:
    """Find a contact Id matching the email address."""
    try:
        db = _get_db()
        result = db.execute(
            "SELECT \"Id\" FROM contact WHERE LOWER(\"Email\") = :email LIMIT 1",
            {"email": email_addr.lower()},
        ).mappings().first()
        db.close()
        if result:
            return result["Id"]
    except Exception as e:
        log.error(f"Contact lookup failed: {e}")
    return None


def sync_outlook_inbox(limit: int = 50) -> int:
    """Poll Outlook INBOX via IMAP and store unseen emails."""
    cfg = _imap_config()
    if not (cfg["user"] and cfg["password"]):
        log.warning("Outlook IMAP credentials not set; skipping inbox sync.")
        return 0

    stored = 0
    try:
        mail = imaplib.IMAP4_SSL(cfg["server"])
        mail.login(cfg["user"], cfg["password"])
        mail.select("inbox")

        # Fetch both unseen and a recent batch so we don't miss anything
        status, messages = mail.search(None, "(UNSEEN)")
        if status != "OK":
            log.warning("IMAP search returned no messages.")
            return 0

        msg_ids = messages[0].split()[-limit:]
        for msg_id in msg_ids:
            status, data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK" or not data:
                continue

            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)

            from_email = _decode_header_value(msg.get("From"))
            to_email = _decode_header_value(msg.get("To"))
            subject = _decode_header_value(msg.get("Subject"))
            message_id = msg.get("Message-ID") or msg.get("Message-Id")
            body = _extract_plain_body(msg)
            contact_id = _match_contact_by_email(from_email)

            _store_email(
                direction="received",
                to_email=to_email,
                from_email=from_email,
                subject=subject,
                body=body,
                status="received",
                source="outlook",
                contact_id=contact_id,
                provider_message_id=message_id,
                received_at=datetime.now(timezone.utc),
            )
            stored += 1

        mail.close()
        mail.logout()
        log.info(f"Outlook listener stored {stored} received emails.")
        return stored

    except Exception as e:
        log.error(f"Outlook inbox sync failed: {e}")
        return 0


def start_outlook_listener(interval: int = 120) -> None:
    """Start a background daemon thread that periodically syncs the Outlook inbox."""
    if not (_imap_config()["user"] and _imap_config()["password"]):
        log.info("Outlook IMAP not configured; auto listener not started.")
        return

    def _loop():
        while True:
            try:
                sync_outlook_inbox(limit=50)
            except Exception as e:
                log.error(f"Outlook listener loop error: {e}")
            # sleep in chunks so the thread can die quickly if needed
            for _ in range(interval):
                # We use a simple thread sleep; in production this could be an Event.
                import time
                time.sleep(1)

    t = threading.Thread(target=_loop, daemon=True, name="outlook-listener")
    t.start()
    log.info("Outlook auto listener started.")
