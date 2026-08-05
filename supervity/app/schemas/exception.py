# app/schemas/exception.py
"""Pydantic schemas for Workbench exception operations."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ExceptionBase(BaseModel):
    type: str
    severity: str = "warning"
    title: str
    description: str = ""
    prospect_id: Optional[str] = None
    account_name: Optional[str] = None
    context: Optional[Any] = None
    ai_recommendation: Optional[str] = None
    ai_confidence: Optional[int] = None


class ExceptionCreate(ExceptionBase):
    pass


class ExceptionResolve(BaseModel):
    resolution_action: str  # approved | rejected | modified
    resolved_by: str = "Admin"
    resolution_notes: Optional[str] = None


class ExceptionRead(ExceptionBase):
    id: int
    status: str = "pending"
    resolved_by: Optional[str] = None
    resolution_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        orm_mode = True
