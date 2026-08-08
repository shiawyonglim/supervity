# app/models/roles.py
"""
Revenue org hierarchy — the escalation chain a lead climbs as it qualifies:

    SDR  ->  Sales Agent  ->  Manager  ->  CRO
  (first net)  (the pitch)   (the closer)  (the overseer)

Each level links to the one above it, so a handover always knows where to send the
account next, and the CRO can reassign anything stranded under an inactive owner.

The SDR level already lives in the raw `sdr_roster` table (seeded from CSV). These
three ORM tables add the levels above it, and `sdr_roster` gains a `sales_agent_id`
column (added in app/core/schema_patch.py) that points a rep at their Sales Agent.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from ..core.database import Base


class CRO(Base):
    """The Overseer — holds master access, reassigns stalled deals."""
    __tablename__ = "cro"

    cro_id = Column(String(50), primary_key=True, index=True)  # e.g. 005CRO01
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Manager(Base):
    """The Closer — runs final calls, writes the SOW, gets the signature."""
    __tablename__ = "manager"

    manager_id = Column(String(50), primary_key=True, index=True)  # e.g. 005MGR01
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    region = Column(String(50))
    # Who this manager reports up to.
    cro_id = Column(String(50), ForeignKey("cro.cro_id"), nullable=True)
    current_capacity = Column(Integer, default=0)
    max_capacity = Column(Integer, default=15)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SalesAgent(Base):
    """The Pitch — calls the prospect, qualifies budget/timeline, tags SQL."""
    __tablename__ = "sales_agent"

    agent_id = Column(String(50), primary_key=True, index=True)  # e.g. 005SA01
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    region = Column(String(50))
    segment = Column(String(50))
    # Who this agent hands closed-qualified deals up to.
    manager_id = Column(String(50), ForeignKey("manager.manager_id"), nullable=True)
    current_capacity = Column(Integer, default=0)
    max_capacity = Column(Integer, default=40)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class HandoverLog(Base):
    """A visible trail of every handover / escalation up the chain."""
    __tablename__ = "handover_log"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(String(50), index=True)
    account_id = Column(String(50), nullable=True)
    from_owner_id = Column(String(50))
    from_role = Column(String(50))
    to_owner_id = Column(String(50))
    to_role = Column(String(50))
    from_stage = Column(String(50), nullable=True)
    to_stage = Column(String(50), nullable=True)
    reason = Column(String(100), default="handover")  # handover | cro_reassign
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
