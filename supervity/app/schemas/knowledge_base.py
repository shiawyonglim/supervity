# app/schemas/knowledge_base.py
"""Pydantic schemas for the Knowledge Base (reference documents + assembled text)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KnowledgeDocumentBase(BaseModel):
    title: str
    category: str = "reference"
    content: str
    is_active: bool = True


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    pass


class KnowledgeDocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class KnowledgeDocument(KnowledgeDocumentBase):
    id: int
    source: str = "manual"
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class KnowledgeBaseText(BaseModel):
    """The full assembled knowledge base — what gets sent to Auto on every run."""
    text: str
    policy_count: int
    document_count: int
    generated_at: datetime
