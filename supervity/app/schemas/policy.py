# app/schemas/policy.py
"""Pydantic schemas for AI Policy CRUD operations."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PolicyBase(BaseModel):
    name: str
    description: str = ""
    natural_language: str
    summary: str = ""
    policy_type: str = "natural_language"
    dsl: Optional[Any] = None
    refined_instruction: Optional[str] = None
    ai_instruction: Optional[str] = None
    entity_name: Optional[str] = None
    is_active: bool = True
    priority: int = 50
    tags: list[str] = []


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    natural_language: Optional[str] = None
    summary: Optional[str] = None
    policy_type: Optional[str] = None
    dsl: Optional[Any] = None
    refined_instruction: Optional[str] = None
    ai_instruction: Optional[str] = None
    entity_name: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    tags: Optional[list[str]] = None


class Policy(PolicyBase):
    id: int
    execution_count: int = 0
    last_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PolicyGenerateRequest(BaseModel):
    prompt: str
    entity_name: Optional[str] = None
