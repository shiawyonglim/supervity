# app/models/insight.py
"""AI Insight model — AI-generated observations about system behavior."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON

from ..core.database import Base


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)          # pattern | anomaly | recommendation
    severity = Column(String(20), default="info")       # critical | warning | info
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    data = Column(JSON, nullable=True)                  # supporting data payload
    suggested_action = Column(Text, nullable=True)
    action_type = Column(String(50), nullable=True)     # create_policy | investigate | review_duplicate
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
