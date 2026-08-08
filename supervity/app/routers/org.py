# app/routers/org.py
"""
Revenue org hierarchy + handover flow.

The escalation chain:  SDR -> Sales Agent -> Manager -> CRO.

- A lead starts owned by an SDR (the first net).
- When it shows interest, the SDR HANDS IT OVER: ownership moves to the SDR's linked
  Sales Agent and the lead stage advances. Same again Agent -> Manager.
- The Manager CLOSES it (stage -> Customer, opportunities -> Closed Won).
- The CRO oversees and can REASSIGN anything stranded under an inactive owner to an
  active peer at the same level.

Every link (which SDR reports to which Agent, which Agent to which Manager, etc.) lives
in the database and can be changed; the flow always follows the current links.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.roles import CRO, HandoverLog, Manager, SalesAgent
from ..services.audit import audit, AuditCategory, AuditSeverity

log = logging.getLogger(__name__)

router = APIRouter(prefix="/org", tags=["Revenue Org & Handover"])

# The sell chain, in order. CRO is oversight, not a step leads pass through.
SELL_CHAIN = ["sdr", "sales_agent", "manager"]

ROLE_LABEL = {
    "sdr": "SDR",
    "sales_agent": "Sales Agent",
    "manager": "Manager",
    "cro": "CRO",
}

# Stage a lead enters when it is handed TO this role.
ENTRY_STAGE = {
    "sales_agent": "MQL",   # SDR got a reply / interest -> Marketing Qualified
    "manager": "SQL",       # Agent qualified budget & timeline -> Sales Qualified
}


# =========================================================================
# OWNER RESOLUTION — an OwnerId can point at any level of the chain
# =========================================================================

def resolve_owner(db: Session, owner_id: str) -> Optional[dict]:
    """Return {role, owner_id, name, active, next_id, ...} for any owner_id, or None."""
    if not owner_id:
        return None

    row = db.execute(
        text(
            "SELECT owner_id, name, email, region, segment, current_capacity, "
            "max_capacity, active, sales_agent_id FROM sdr_roster WHERE owner_id = :id"
        ),
        {"id": owner_id},
    ).mappings().first()
    if row:
        d = dict(row)
        return {"role": "sdr", "owner_id": d["owner_id"], "name": d["name"],
                "email": d.get("email"), "region": d.get("region"), "segment": d.get("segment"),
                "active": bool(d.get("active")), "next_id": d.get("sales_agent_id"),
                "current_capacity": d.get("current_capacity"), "max_capacity": d.get("max_capacity")}

    a = db.get(SalesAgent, owner_id)
    if a:
        return {"role": "sales_agent", "owner_id": a.agent_id, "name": a.name, "email": a.email,
                "region": a.region, "segment": a.segment, "active": a.active, "next_id": a.manager_id,
                "current_capacity": a.current_capacity, "max_capacity": a.max_capacity}

    m = db.get(Manager, owner_id)
    if m:
        return {"role": "manager", "owner_id": m.manager_id, "name": m.name, "email": m.email,
                "region": m.region, "segment": None, "active": m.active, "next_id": m.cro_id,
                "current_capacity": m.current_capacity, "max_capacity": m.max_capacity}

    c = db.get(CRO, owner_id)
    if c:
        return {"role": "cro", "owner_id": c.cro_id, "name": c.name, "email": c.email,
                "region": None, "segment": None, "active": c.active, "next_id": None,
                "current_capacity": None, "max_capacity": None}

    return None


def _adjust_capacity(db: Session, owner: dict, delta: int) -> None:
    """Nudge a person's current_capacity as work moves on/off their plate."""
    role = owner["role"]
    oid = owner["owner_id"]
    if role == "sdr":
        db.execute(
            text("UPDATE sdr_roster SET current_capacity = GREATEST(0, COALESCE(current_capacity,0) + :d) WHERE owner_id = :id"),
            {"d": delta, "id": oid},
        )
    elif role == "sales_agent":
        obj = db.get(SalesAgent, oid)
        if obj:
            obj.current_capacity = max(0, (obj.current_capacity or 0) + delta)
    elif role == "manager":
        obj = db.get(Manager, oid)
        if obj:
            obj.current_capacity = max(0, (obj.current_capacity or 0) + delta)


# =========================================================================
# HIERARCHY VIEW
# =========================================================================

@router.get("/hierarchy")
def get_hierarchy(db: Session = Depends(get_db)):
    """Full org tree: CRO -> Managers -> Sales Agents -> SDRs."""
    cros = db.query(CRO).all()
    managers = db.query(Manager).all()
    agents = db.query(SalesAgent).all()
    sdrs = db.execute(text(
        "SELECT owner_id, name, email, region, segment, current_capacity, "
        "max_capacity, active, sales_agent_id FROM sdr_roster"
    )).mappings().all()
    sdrs = [dict(s) for s in sdrs]

    def agent_node(a: SalesAgent):
        return {
            "agent_id": a.agent_id, "name": a.name, "email": a.email, "region": a.region,
            "segment": a.segment, "active": a.active,
            "current_capacity": a.current_capacity, "max_capacity": a.max_capacity,
            "manager_id": a.manager_id,
            "sdrs": [
                {"owner_id": s["owner_id"], "name": s["name"], "region": s.get("region"),
                 "segment": s.get("segment"), "active": bool(s.get("active")),
                 "current_capacity": s.get("current_capacity"), "max_capacity": s.get("max_capacity")}
                for s in sdrs if s.get("sales_agent_id") == a.agent_id
            ],
        }

    def manager_node(m: Manager):
        return {
            "manager_id": m.manager_id, "name": m.name, "email": m.email, "region": m.region,
            "active": m.active, "current_capacity": m.current_capacity, "max_capacity": m.max_capacity,
            "cro_id": m.cro_id,
            "agents": [agent_node(a) for a in agents if a.manager_id == m.manager_id],
        }

    tree = [
        {
            "cro_id": c.cro_id, "name": c.name, "email": c.email, "active": c.active,
            "managers": [manager_node(m) for m in managers if m.cro_id == c.cro_id],
        }
        for c in cros
    ]

    # SDRs / agents / managers not attached to anything above them (visibility for editing).
    unassigned_sdrs = [s for s in sdrs if not s.get("sales_agent_id")]
    orphan_agents = [agent_node(a) for a in agents if not a.manager_id]
    orphan_managers = [manager_node(m) for m in managers if not m.cro_id]

    return {
        "hierarchy": tree,
        "unassigned_sdrs": unassigned_sdrs,
        "orphan_agents": orphan_agents,
        "orphan_managers": orphan_managers,
        "counts": {"cros": len(cros), "managers": len(managers), "agents": len(agents), "sdrs": len(sdrs)},
    }


@router.get("/chain/{owner_id}")
def get_chain(owner_id: str, db: Session = Depends(get_db)):
    """Resolve one person and the full chain above them (who they escalate to)."""
    chain = []
    current = resolve_owner(db, owner_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"No owner found with id {owner_id}")

    seen = set()
    node = current
    while node and node["owner_id"] not in seen:
        seen.add(node["owner_id"])
        chain.append({"role": node["role"], "role_label": ROLE_LABEL[node["role"]],
                      "owner_id": node["owner_id"], "name": node["name"], "active": node["active"]})
        node = resolve_owner(db, node["next_id"]) if node.get("next_id") else None

    return {"owner_id": owner_id, "chain": chain}


# =========================================================================
# EDIT THE LINKS (change reporting lines in the database)
# =========================================================================

class SdrLinkUpdate(BaseModel):
    sales_agent_id: Optional[str] = None
    active: Optional[bool] = None
    max_capacity: Optional[int] = None
    current_capacity: Optional[int] = None


class AgentUpdate(BaseModel):
    manager_id: Optional[str] = None
    active: Optional[bool] = None
    max_capacity: Optional[int] = None


class ManagerUpdate(BaseModel):
    cro_id: Optional[str] = None
    active: Optional[bool] = None
    max_capacity: Optional[int] = None


@router.patch("/sdr/{owner_id}")
def update_sdr_link(owner_id: str, body: SdrLinkUpdate, db: Session = Depends(get_db)):
    """Re-point an SDR at a different Sales Agent, or toggle them active/inactive."""
    row = db.execute(text("SELECT owner_id FROM sdr_roster WHERE owner_id = :id"), {"id": owner_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="SDR not found")

    if body.sales_agent_id is not None:
        if body.sales_agent_id and not db.get(SalesAgent, body.sales_agent_id):
            raise HTTPException(status_code=400, detail=f"Sales agent {body.sales_agent_id} does not exist")
        db.execute(text("UPDATE sdr_roster SET sales_agent_id = :sa WHERE owner_id = :id"),
                   {"sa": body.sales_agent_id, "id": owner_id})
    if body.active is not None:
        db.execute(text("UPDATE sdr_roster SET active = :a WHERE owner_id = :id"),
                   {"a": body.active, "id": owner_id})
    if body.max_capacity is not None:
        db.execute(text("UPDATE sdr_roster SET max_capacity = :m WHERE owner_id = :id"),
                   {"m": body.max_capacity, "id": owner_id})
    if body.current_capacity is not None:
        db.execute(text("UPDATE sdr_roster SET current_capacity = :c WHERE owner_id = :id"),
                   {"c": body.current_capacity, "id": owner_id})
    db.commit()
    return {"status": "success", "owner_id": owner_id, **body.model_dump(exclude_unset=True)}


@router.patch("/agent/{agent_id}")
def update_agent(agent_id: str, body: AgentUpdate, db: Session = Depends(get_db)):
    """Re-point a Sales Agent at a different Manager, toggle active, or set capacity."""
    agent = db.get(SalesAgent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Sales agent not found")
    if body.manager_id is not None:
        if body.manager_id and not db.get(Manager, body.manager_id):
            raise HTTPException(status_code=400, detail=f"Manager {body.manager_id} does not exist")
        agent.manager_id = body.manager_id
    if body.active is not None:
        agent.active = body.active
    if body.max_capacity is not None:
        agent.max_capacity = body.max_capacity
    db.commit()
    return {"status": "success", "agent_id": agent_id, **body.model_dump(exclude_unset=True)}


@router.patch("/manager/{manager_id}")
def update_manager(manager_id: str, body: ManagerUpdate, db: Session = Depends(get_db)):
    """Re-point a Manager at a different CRO, toggle active, or set capacity."""
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    if body.cro_id is not None:
        if body.cro_id and not db.get(CRO, body.cro_id):
            raise HTTPException(status_code=400, detail=f"CRO {body.cro_id} does not exist")
        manager.cro_id = body.cro_id
    if body.active is not None:
        manager.active = body.active
    if body.max_capacity is not None:
        manager.max_capacity = body.max_capacity
    db.commit()
    return {"status": "success", "manager_id": manager_id, **body.model_dump(exclude_unset=True)}


# =========================================================================
# HANDOVER — advance a contact one level up the chain
# =========================================================================

class HandoverRequest(BaseModel):
    note: Optional[str] = None
    stage: Optional[str] = None  # optional explicit lead stage override


class CloseRequest(BaseModel):
    note: Optional[str] = None


def _load_contact(db: Session, contact_id: str) -> dict:
    row = db.execute(
        text('SELECT "Id", "OwnerId", "Owner_Name", "Lead_Stage__c", "AccountId" '
             'FROM contact WHERE "Id" = :id'),
        {"id": contact_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
    return dict(row)


@router.post("/handover/{contact_id}")
def handover_contact(contact_id: str, body: HandoverRequest, db: Session = Depends(get_db)):
    """
    Hand a contact up to the next level: SDR -> Sales Agent -> Manager.
    Moves ownership, advances the lead stage, adjusts capacity, and logs the handover.
    """
    contact = _load_contact(db, contact_id)
    current_owner = resolve_owner(db, contact["OwnerId"])
    if not current_owner:
        raise HTTPException(status_code=400, detail=f"Contact's current owner '{contact['OwnerId']}' is not in the org — assign it to an SDR first.")

    role = current_owner["role"]
    if role == "manager":
        raise HTTPException(status_code=400, detail="Contact is already with a Manager — use /org/close to close the deal.")
    if role == "cro":
        raise HTTPException(status_code=400, detail="A CRO does not receive handovers.")

    next_id = current_owner.get("next_id")
    if not next_id:
        role_label = ROLE_LABEL[role]
        raise HTTPException(status_code=400, detail=f"{current_owner['name']} ({role_label}) has no {'Sales Agent' if role == 'sdr' else 'Manager'} linked — set the link first.")

    next_owner = resolve_owner(db, next_id)
    if not next_owner:
        raise HTTPException(status_code=400, detail=f"Linked owner '{next_id}' does not exist.")
    if not next_owner["active"]:
        raise HTTPException(status_code=409, detail=f"{next_owner['name']} ({ROLE_LABEL[next_owner['role']]}) is inactive — the CRO should reassign or you should re-point the link before handover.")

    new_stage = body.stage or ENTRY_STAGE.get(next_owner["role"])
    from_stage = contact.get("Lead_Stage__c")

    # Move ownership + stage on the contact.
    db.execute(
        text('UPDATE contact SET "OwnerId" = :oid, "Owner_Name" = :oname, "Lead_Stage__c" = :stage WHERE "Id" = :id'),
        {"oid": next_owner["owner_id"], "oname": next_owner["name"], "stage": new_stage, "id": contact_id},
    )

    # Shift the workload marker.
    _adjust_capacity(db, current_owner, -1)
    _adjust_capacity(db, next_owner, +1)

    default_note = (
        f"{current_owner['name']} ({ROLE_LABEL[role]}) handed lead to "
        f"{next_owner['name']} ({ROLE_LABEL[next_owner['role']]}); stage {from_stage} -> {new_stage}."
    )
    note = body.note or default_note

    entry = HandoverLog(
        contact_id=contact_id, account_id=contact.get("AccountId"),
        from_owner_id=current_owner["owner_id"], from_role=role,
        to_owner_id=next_owner["owner_id"], to_role=next_owner["role"],
        from_stage=from_stage, to_stage=new_stage, reason="handover", note=note,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    audit.log_sync(
        action="org.handover",
        description=note,
        category=AuditCategory.DATA,
        severity=AuditSeverity.INFO,
        resource_type="contact",
        resource_id=contact_id,
        metadata={"from": current_owner["owner_id"], "to": next_owner["owner_id"],
                  "from_stage": from_stage, "to_stage": new_stage},
        actor={"id": "system", "email": "org_flow@supervity.ai"},
    )

    return {
        "status": "success",
        "handover_id": entry.id,
        "contact_id": contact_id,
        "from": {"owner_id": current_owner["owner_id"], "name": current_owner["name"], "role": ROLE_LABEL[role]},
        "to": {"owner_id": next_owner["owner_id"], "name": next_owner["name"], "role": ROLE_LABEL[next_owner["role"]]},
        "stage": {"from": from_stage, "to": new_stage},
        "note": note,
    }


@router.post("/close/{contact_id}")
def close_deal(contact_id: str, body: CloseRequest, db: Session = Depends(get_db)):
    """Manager closes: lead stage -> Customer, the contact's open opportunities -> Closed Won."""
    contact = _load_contact(db, contact_id)
    owner = resolve_owner(db, contact["OwnerId"])
    if not owner or owner["role"] != "manager":
        raise HTTPException(status_code=400, detail="Only a Manager can close a deal — hand the contact up to a Manager first.")

    from_stage = contact.get("Lead_Stage__c")
    db.execute(text('UPDATE contact SET "Lead_Stage__c" = :s WHERE "Id" = :id'),
               {"s": "Customer", "id": contact_id})

    won = db.execute(
        text('UPDATE opportunity SET "StageName" = \'Closed Won\', "IsClosed" = true, "IsWon" = true '
             'WHERE "ContactId" = :id AND ("IsClosed" = false OR "IsClosed" IS NULL)'),
        {"id": contact_id},
    ).rowcount

    _adjust_capacity(db, owner, -1)

    close_note = body.note or f"{owner['name']} (Manager) closed the deal — signature secured. {won} opportunity(ies) marked Closed Won."
    db.add(HandoverLog(
        contact_id=contact_id, account_id=contact.get("AccountId"),
        from_owner_id=owner["owner_id"], from_role="manager",
        to_owner_id=owner["owner_id"], to_role="manager",
        from_stage=from_stage, to_stage="Customer", reason="close", note=close_note,
    ))
    db.commit()

    audit.log_sync(
        action="org.close", description=close_note, category=AuditCategory.DATA,
        severity=AuditSeverity.INFO, resource_type="contact", resource_id=contact_id,
        actor={"id": "system", "email": "org_flow@supervity.ai"},
    )
    return {"status": "success", "contact_id": contact_id, "stage": {"from": from_stage, "to": "Customer"},
            "opportunities_won": won, "note": close_note}


# =========================================================================
# CRO OVERSIGHT — reassign anything stranded under an inactive owner
# =========================================================================

def _active_peers(db: Session, role: str, region: Optional[str], segment: Optional[str], exclude_id: str):
    """Active people at the same level, preferring the same region/segment, least loaded first."""
    if role == "sdr":
        rows = db.execute(text(
            "SELECT owner_id, name, region, segment, current_capacity, max_capacity "
            "FROM sdr_roster WHERE active = true AND owner_id <> :ex"
        ), {"ex": exclude_id}).mappings().all()
        peers = [dict(r) for r in rows]
    elif role == "sales_agent":
        peers = [{"owner_id": a.agent_id, "name": a.name, "region": a.region, "segment": a.segment,
                  "current_capacity": a.current_capacity, "max_capacity": a.max_capacity}
                 for a in db.query(SalesAgent).filter(SalesAgent.active == True, SalesAgent.agent_id != exclude_id).all()]
    elif role == "manager":
        peers = [{"owner_id": m.manager_id, "name": m.name, "region": m.region, "segment": None,
                  "current_capacity": m.current_capacity, "max_capacity": m.max_capacity}
                 for m in db.query(Manager).filter(Manager.active == True, Manager.manager_id != exclude_id).all()]
    else:
        peers = []

    def score(p):
        region_match = 0 if (region and p.get("region") == region) else 1
        segment_match = 0 if (segment and p.get("segment") == segment) else 1
        util = (p.get("current_capacity") or 0) / max(1, (p.get("max_capacity") or 1))
        return (region_match, segment_match, util)

    peers.sort(key=score)
    return peers


@router.post("/cro/reassign-stalled")
def cro_reassign_stalled(db: Session = Depends(get_db)):
    """
    CRO action: scan for contacts owned by an INACTIVE person anywhere in the chain and
    reassign each to an active peer at the same level (preferring same region/segment,
    least loaded). This is the "deal froze because someone went inactive" recovery.
    """
    owned = db.execute(text(
        'SELECT "Id", "OwnerId", "Owner_Name", "AccountId", "Lead_Stage__c" '
        'FROM contact WHERE "OwnerId" IS NOT NULL AND "OwnerId" <> \'\''
    )).mappings().all()

    reassignments = []
    # Cache owner resolutions so we don't re-hit the DB per contact.
    owner_cache: dict = {}

    for c in owned:
        oid = c["OwnerId"]
        if oid not in owner_cache:
            owner_cache[oid] = resolve_owner(db, oid)
        owner = owner_cache[oid]
        # Only act on owners that exist in the org AND are inactive.
        if not owner or owner["active"]:
            continue

        peers = _active_peers(db, owner["role"], owner.get("region"), owner.get("segment"), owner["owner_id"])
        if not peers:
            continue
        new = peers[0]

        db.execute(
            text('UPDATE contact SET "OwnerId" = :oid, "Owner_Name" = :oname WHERE "Id" = :id'),
            {"oid": new["owner_id"], "oname": new["name"], "id": c["Id"]},
        )
        _adjust_capacity(db, {"role": owner["role"], "owner_id": new["owner_id"]}, +1)

        note = (
            f"CRO reassigned {c['Id']} from inactive {owner['name']} ({ROLE_LABEL[owner['role']]}) "
            f"to {new['name']} ({ROLE_LABEL[owner['role']]})."
        )
        db.add(HandoverLog(
            contact_id=c["Id"], account_id=c.get("AccountId"),
            from_owner_id=owner["owner_id"], from_role=owner["role"],
            to_owner_id=new["owner_id"], to_role=owner["role"],
            from_stage=c.get("Lead_Stage__c"), to_stage=c.get("Lead_Stage__c"),
            reason="cro_reassign", note=note,
        ))
        reassignments.append({
            "contact_id": c["Id"], "role": ROLE_LABEL[owner["role"]],
            "from": {"owner_id": owner["owner_id"], "name": owner["name"]},
            "to": {"owner_id": new["owner_id"], "name": new["name"]},
        })

    db.commit()

    if reassignments:
        audit.log_sync(
            action="org.cro_reassign",
            description=f"CRO reassigned {len(reassignments)} stalled contact(s) from inactive owners to active peers.",
            category=AuditCategory.DATA, severity=AuditSeverity.WARNING,
            resource_type="contact",
            metadata={"count": len(reassignments)},
            actor={"id": "system", "email": "cro@supervity.ai"},
        )

    return {"status": "success", "reassigned_count": len(reassignments), "reassignments": reassignments}


# =========================================================================
# HANDOVER HISTORY
# =========================================================================

@router.get("/handovers")
def list_handovers(limit: int = 50, contact_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Recent handover / escalation trail."""
    q = db.query(HandoverLog).order_by(HandoverLog.created_at.desc())
    if contact_id:
        q = q.filter(HandoverLog.contact_id == contact_id)
    rows = q.limit(limit).all()
    return {
        "count": len(rows),
        "handovers": [
            {"id": r.id, "contact_id": r.contact_id, "reason": r.reason,
             "from": {"owner_id": r.from_owner_id, "role": ROLE_LABEL.get(r.from_role, r.from_role)},
             "to": {"owner_id": r.to_owner_id, "role": ROLE_LABEL.get(r.to_role, r.to_role)},
             "stage": {"from": r.from_stage, "to": r.to_stage},
             "note": r.note, "created_at": r.created_at}
            for r in rows
        ],
    }
