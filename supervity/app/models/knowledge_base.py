# app/models/knowledge_base.py
"""Knowledge Base model — reference documents that ground the AI agents.

The Knowledge Base is the text corpus the Orchestrator/Operators are given on every
run, alongside the active AI Policies. It holds domain reference material (ICP scoring
rules, consent/compliance rules, routing & capacity rules, sequence eligibility, etc.)
that a business user can edit in plain text with no code — exactly like a Policy, but
descriptive rather than a constraint that gates an action.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from ..core.database import Base


class KnowledgeDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="reference")  # reference | operator_instruction | custom
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    source = Column(String(50), default="manual")  # manual | seed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
