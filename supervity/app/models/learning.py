# app/models/learning.py
"""AI learning table: patterns the AI observes from emails, human actions and workflows."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, func

from ..core.database import Base


class Learning(Base):
    __tablename__ = "learning"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # The contact this insight is tied to, or None for general insights
    contact_id = Column(String(50), nullable=True, index=True)

    # What the AI learned: 'writing_style', 'response_pattern', 'intent_signal',
    # 'policy_effectiveness', 'buying_signal', 'objection', 'tone'
    category = Column(String(50), nullable=False, index=True)

    # Where the insight came from: 'email', 'human_action', 'outlook_listener',
    # 'workflow', 'dashboard', 'manual'
    source = Column(String(50), nullable=False)

    # Human-readable insight text
    insight = Column(Text, nullable=False)

    # A sample text that supports the insight (e.g. a customer quote)
    sample_text = Column(Text, nullable=True)

    # Model / workflow confidence 0-100
    confidence = Column(Float, default=0.0)

    # Whether a human has reviewed this learning
    reviewed = Column(Boolean, default=False)

    # Which policy (if any) this learning was folded into
    applied_in_policy = Column(String(255), nullable=True)

    # Flexible extra data
    extra_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
