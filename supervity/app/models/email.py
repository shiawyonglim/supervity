# app/models/email.py
"""Email log: every email sent or received through the app or Outlook."""

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func

from ..core.database import Base


class EmailLog(Base):
    __tablename__ = "email_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    contact_id = Column(String(50), nullable=True, index=True)
    thread_id = Column(String(100), nullable=True, index=True)

    # 'sent' or 'received'
    direction = Column(String(10), default="sent", nullable=False)
    # 'queued', 'sent', 'failed', 'received'
    status = Column(String(20), default="queued", nullable=False)
    # 'manual', 'outlook', 'workflow', 'ai'
    source = Column(String(50), default="manual", nullable=False)

    from_email = Column(String(255), nullable=True)
    to_email = Column(String(255), nullable=True)
    cc = Column(JSON, nullable=True)
    bcc = Column(JSON, nullable=True)

    subject = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    body_preview = Column(Text, nullable=True)

    # Provider-side message id (e.g. Outlook Message-Id)
    provider_message_id = Column(String(255), nullable=True, index=True)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Extra metadata such as smtp response, error, etc.
    extra_metadata = Column(JSON, nullable=True)
