# app/models/context.py
"""Contact context: human-readable snippets that help users understand a customer."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from ..core.database import Base


class ContactContext(Base):
    __tablename__ = "contact_context"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # The contact this context belongs to
    contact_id = Column(String(50), nullable=False, index=True)

    # Type of context: 'visitor_activity', 'email_history', 'account_info',
    # 'intent_summary', 'privacy_note', 'ai_summary', 'policy_note', 'learning'
    context_type = Column(String(50), nullable=False, index=True)

    # The actual human-readable content
    content = Column(Text, nullable=False)

    # Who/what generated it: 'ai', 'user', 'system'
    generated_by = Column(String(20), default="ai", nullable=False)

    # Higher priority contexts show first
    priority = Column(Integer, default=0)

    # Soft delete: inactive contexts are hidden
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
