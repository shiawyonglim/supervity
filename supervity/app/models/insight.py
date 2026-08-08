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

    # --- WHO / WHAT NOW / WHAT IF NOT ---------------------------------------
    # Every insight must answer three questions so it is directly actionable:
    #   1. owner_*        — WHO is this for?
    #   2. suggested_action — WHAT should they do now?
    #   3. consequence    — WHAT happens if they don't?
    owner_name = Column(String(255), nullable=True)     # e.g. "Wei Ho" or "Revenue Ops Manager"
    owner_role = Column(String(150), nullable=True)     # e.g. "SDR — MY Enterprise"
    owner_id = Column(String(50), nullable=True)        # SDR_Roster.owner_id (005...) when resolvable
    suggested_action = Column(Text, nullable=True)      # what to do now
    consequence = Column(Text, nullable=True)           # what happens if they don't act

    action_type = Column(String(50), nullable=True)     # create_policy | investigate | review_duplicate
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
