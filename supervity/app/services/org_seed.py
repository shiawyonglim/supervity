# app/services/org_seed.py
"""
Seed the revenue org hierarchy (CRO -> Managers -> Sales Agents) and link each
existing SDR to a Sales Agent. Idempotent: only fills what is missing, never
overwrites links an admin has since edited in the database.

Structure seeded:

    CRO  005CRO01  Rohan Mehta (The Overseer)
     ├─ MGR 005MGR01  Enterprise Closer   (MY / SG / IN Enterprise)
     │    ├─ SA 005SA01  APAC Enterprise Agent   <- SDRs 005AE1 (MY Ent), 005AE3 (SG Ent)
     │    └─ SA 005SA02  India Enterprise Agent   <- SDR  005AE5 (IN Ent)
     └─ MGR 005MGR02  Growth Closer       (Mid-Market / SMB)
          └─ SA 005SA03  Growth & SMB Agent      <- SDRs 005AE2, 005AE4, 005AE6
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.roles import CRO, Manager, SalesAgent

log = logging.getLogger(__name__)

SEED_CRO = {
    "cro_id": "005CRO01",
    "name": "Rohan Mehta",
    "email": "rohan.mehta@supervity.ai",
    "active": True,
}

SEED_MANAGERS = [
    {"manager_id": "005MGR01", "name": "Elena Fischer", "email": "elena.fischer@supervity.ai",
     "region": "APAC-Enterprise", "cro_id": "005CRO01", "current_capacity": 4, "max_capacity": 15, "active": True},
    {"manager_id": "005MGR02", "name": "David Okoro", "email": "david.okoro@supervity.ai",
     "region": "APAC-Growth", "cro_id": "005CRO01", "current_capacity": 3, "max_capacity": 15, "active": True},
]

SEED_AGENTS = [
    {"agent_id": "005SA01", "name": "Hana Kim", "email": "hana.kim@supervity.ai",
     "region": "APAC", "segment": "Enterprise", "manager_id": "005MGR01",
     "current_capacity": 12, "max_capacity": 40, "active": True},
    {"agent_id": "005SA02", "name": "Vikram Sethi", "email": "vikram.sethi@supervity.ai",
     "region": "IN", "segment": "Enterprise", "manager_id": "005MGR01",
     "current_capacity": 8, "max_capacity": 40, "active": True},
    {"agent_id": "005SA03", "name": "Nadia Rahman", "email": "nadia.rahman@supervity.ai",
     "region": "APAC", "segment": "Growth", "manager_id": "005MGR02",
     "current_capacity": 15, "max_capacity": 40, "active": True},
]

# Which Sales Agent each SDR hands qualified leads up to.
SDR_TO_AGENT = {
    "005AE1": "005SA01",  # Mei Chen — MY Enterprise
    "005AE2": "005SA03",  # Arjun Prakash — IN Mid-Market
    "005AE3": "005SA01",  # Wei Ho — SG Enterprise
    "005AE4": "005SA03",  # Priya Nair — TH SMB
    "005AE5": "005SA02",  # Sanjay Rao — IN Enterprise
    "005AE6": "005SA03",  # Grace Lim — MY Mid-Market
}


def seed_org_hierarchy(db: Session) -> None:
    """Insert CRO/Managers/Agents if missing, and backfill sdr_roster.sales_agent_id."""
    try:
        if not db.get(CRO, SEED_CRO["cro_id"]):
            db.add(CRO(**SEED_CRO))

        for m in SEED_MANAGERS:
            if not db.get(Manager, m["manager_id"]):
                db.add(Manager(**m))

        for a in SEED_AGENTS:
            if not db.get(SalesAgent, a["agent_id"]):
                db.add(SalesAgent(**a))

        db.commit()

        # Backfill the SDR -> Sales Agent links only where they are still empty,
        # so an admin who re-points a rep in the DB is never overwritten on reboot.
        for sdr_id, agent_id in SDR_TO_AGENT.items():
            db.execute(
                text(
                    "UPDATE sdr_roster SET sales_agent_id = :agent_id "
                    "WHERE owner_id = :sdr_id AND (sales_agent_id IS NULL OR sales_agent_id = '')"
                ),
                {"agent_id": agent_id, "sdr_id": sdr_id},
            )
        db.commit()
        log.info("Revenue org hierarchy verified/seeded.")
    except Exception as e:
        log.error(f"Failed to seed org hierarchy: {e}")
        db.rollback()
