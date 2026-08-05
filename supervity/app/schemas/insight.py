# app/schemas/insight.py
"""Pydantic schemas for AI Insight operations."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class InsightBase(BaseModel):
    type: str  # pattern | anomaly | recommendation
    severity: str = "info"
    title: str
    description: str = ""
    data: Optional[Any] = None
    suggested_action: Optional[str] = None
    action_type: Optional[str] = None
    confidence: float = 0.0


class InsightCreate(InsightBase):
    pass


class Insight(InsightBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
