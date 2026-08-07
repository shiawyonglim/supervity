"""Deduplication Configuration Model."""

from sqlalchemy import Column, Integer, String, Float, DateTime, func
from ..core.database import Base

class DedupConfig(Base):
    __tablename__ = "dedup_config"

    id = Column(Integer, primary_key=True, index=True)
    confidence_threshold = Column(Float, default=80.0)
    match_strategy = Column(String(50), default="Exact Email Match")
    updated_by = Column(String(100), default="System")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
