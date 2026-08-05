# app/models/exception.py
"""Workbench Exception model — items routed to humans when AI can't decide."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON

from ..core.database import Base


class Exception(Base):
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)        # low_confidence | policy_conflict | missing_data | high_stakes | novel_scenario
    severity = Column(String(20), default="warning")  # critical | warning | info
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    prospect_id = Column(String(18), nullable=True)   # FK to contact.Id
    account_name = Column(String(255), nullable=True)
    context = Column(JSON, nullable=True)              # full payload for human review
    ai_recommendation = Column(Text, nullable=True)    # what the AI would do
    ai_confidence = Column(Integer, nullable=True)     # 0-100
    status = Column(String(20), default="pending")     # pending | resolved | dismissed
    resolved_by = Column(String(100), nullable=True)
    resolution_action = Column(String(50), nullable=True)  # approved | rejected | modified
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
