# app/models/policy.py
"""AI Policy model — business rules that constrain agent behavior."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON

from ..core.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    natural_language = Column(Text, nullable=False)
    summary = Column(Text, default="")
    policy_type = Column(String(50), default="natural_language")  # logical | natural_language
    dsl = Column(JSON, nullable=True)  # structured IF/THEN rules
    refined_instruction = Column(Text, nullable=True)
    ai_instruction = Column(Text, nullable=True)
    entity_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=50)
    tags = Column(JSON, default=list)
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
