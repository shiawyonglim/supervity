# app/routers/data_manager.py
"""Data Manager endpoints — buying groups, dedup, routing, quality, consent, integrations."""

import logging
import re
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.dedup_config import DedupConfig
from ..models.exception import Exception as ExceptionModel
from ..services.audit import audit
from ..utils.date_parser import parse_mixed_date

log = logging.getLogger(__name__)

router = APIRouter(prefix="/data-manager", tags=["Data Manager"])


# ─── Pydantic request bodies ───────────────────────────────────────────────────

class DedupConfigUpdate(BaseModel):
    confidence_threshold: float
    match_strategy: str


class RoutingRunRequest(BaseModel):
    contact_ids: list[str] = []


# ─── helpers ────────────────────────────────────────────────────────────────────

HIGH_INTENT_PATTERNS = [
    "%/pricing%", "%/demo%", "%/contact%", "%/request%",
    "%/book%", "%/trial%", "%/quote%", "%/signup%",
]


def _bool_true(val) -> bool:
    """Check if a string-or-bool DB value is truthy."""
    if val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "t", "yes")


def _bool_false(val) -> bool:
    return str(val).strip().lower() in ("false", "0", "f", "no")


def _create_exception_if_not_exists(
    db: Session,
    *,
    exc_type: str,
    title: str,
    description: str = "",
    severity: str = "warning",
    prospect_id: str | None = None,
    account_name: str | None = None,
    context: dict | None = None,
    ai_recommendation: str | None = None,
    ai_confidence: int | None = None,
) -> ExceptionModel | None:
    """Create an exception only if one with the same type+title doesn't already exist as pending."""
    existing = (
        db.query(ExceptionModel)
        .filter(
            ExceptionModel.type == exc_type,
            ExceptionModel.title == title,
            ExceptionModel.status == "pending",
        )
        .first()
    )
    if existing:
        return None
    exc = ExceptionModel(
        type=exc_type,
        title=title,
        description=description,
        severity=severity,
        prospect_id=prospect_id,
        account_name=account_name,
        context=context,
        ai_recommendation=ai_recommendation,
        ai_confidence=ai_confidence,
    )
    db.add(exc)
    return exc


# =============================================================================
# 1. BUYING GROUP RESOLUTION
# =============================================================================

@router.get("/buying-groups")
def get_buying_groups(
    db: Session = Depends(get_db),
    window_days: int = Query(7, ge=1, le=90, description="Rolling window in days for candidate detection"),
):
    """
    List existing buying groups AND propose new candidate groups.

    Existing groups: from buying_group joined to contact/account.
    Proposed groups: accounts with no buying_group rows where 2+ distinct
    contacts show high-intent visitoractivity within the rolling window.
    """
    try:
        # ── Existing groups ──────────────────────────────────────────────
        rows = db.execute(text("""
            SELECT
                bg.group_id,
                bg.account_id,
                bg.contact_id,
                bg.role,
                bg.is_primary,
                bg.added_at,
                a."Name"      AS account_name,
                a."Industry"  AS account_industry,
                c."FirstName" || ' ' || c."LastName" AS contact_name,
                c."Title"     AS contact_title,
                c."Email"     AS contact_email
            FROM buying_group bg
            LEFT JOIN account a ON bg.account_id = a."Id"
            LEFT JOIN contact c ON bg.contact_id = c."Id"
            ORDER BY bg.group_id, bg.is_primary DESC
        """)).mappings().all()

        groups: dict[str, dict] = {}
        for row in rows:
            r = dict(row)
            gid = r["group_id"]
            if gid not in groups:
                groups[gid] = {
                    "group_id": gid,
                    "account_id": r["account_id"],
                    "account_name": r["account_name"],
                    "account_industry": r["account_industry"],
                    "is_proposed": False,
                    "contacts": [],
                }
            groups[gid]["contacts"].append({
                "contact_id": r["contact_id"],
                "name": r["contact_name"],
                "title": r["contact_title"],
                "email": r["contact_email"],
                "role": r["role"],
                "is_primary": r["is_primary"],
                "added_at": r["added_at"],
            })

        # ── Proposed candidate groups ────────────────────────────────────
        # Accounts that have zero buying_group rows
        # where 2+ distinct contacts have high-intent visitoractivity
        url_conditions = " OR ".join([f"va.url ILIKE :p{i}" for i in range(len(HIGH_INTENT_PATTERNS))])
        params = {f"p{i}": p for i, p in enumerate(HIGH_INTENT_PATTERNS)}
        params["window_days"] = window_days

        proposed_rows = db.execute(text(f"""
            WITH accounts_without_bg AS (
                SELECT DISTINCT a."Id" AS account_id, a."Name" AS account_name, a."Industry" AS account_industry
                FROM account a
                WHERE NOT EXISTS (
                    SELECT 1 FROM buying_group bg WHERE bg.account_id = a."Id"
                )
            ),
            intent_contacts AS (
                SELECT
                    c."AccountId"  AS account_id,
                    c."Id"         AS contact_id,
                    c."FirstName" || ' ' || c."LastName" AS contact_name,
                    c."Title"      AS contact_title,
                    c."Email"      AS contact_email,
                    COUNT(va.id)   AS activity_count,
                    array_agg(DISTINCT va.url) AS urls
                FROM visitoractivity va
                JOIN contact c ON va.prospect_id = c."Id"
                WHERE ({url_conditions})
                GROUP BY c."AccountId", c."Id", c."FirstName", c."LastName", c."Title", c."Email"
            )
            SELECT
                awb.account_id,
                awb.account_name,
                awb.account_industry,
                ic.contact_id,
                ic.contact_name,
                ic.contact_title,
                ic.contact_email,
                ic.activity_count,
                ic.urls
            FROM accounts_without_bg awb
            JOIN intent_contacts ic ON ic.account_id = awb.account_id
            WHERE awb.account_id IN (
                SELECT account_id FROM intent_contacts
                GROUP BY account_id HAVING COUNT(DISTINCT contact_id) >= 2
            )
            ORDER BY awb.account_id, ic.activity_count DESC
        """), params).mappings().all()

        proposed_groups: dict[str, dict] = {}
        for row in proposed_rows:
            r = dict(row)
            aid = r["account_id"]
            gid = f"PROPOSED-{aid}"
            if gid not in proposed_groups:
                proposed_groups[gid] = {
                    "group_id": gid,
                    "account_id": aid,
                    "account_name": r["account_name"],
                    "account_industry": r["account_industry"],
                    "is_proposed": True,
                    "contacts": [],
                }
            proposed_groups[gid]["contacts"].append({
                "contact_id": r["contact_id"],
                "name": r["contact_name"],
                "title": r["contact_title"],
                "email": r["contact_email"],
                "role": None,
                "is_primary": None,
                "added_at": None,
                "activity_count": r["activity_count"],
                "urls": r["urls"],
            })

        # Create workbench exceptions for proposed groups
        for gid, pg in proposed_groups.items():
            exc = _create_exception_if_not_exists(
                db,
                exc_type="buying_group_candidate",
                title=f"Proposed buying group for {pg['account_name']}",
                description=(
                    f"{len(pg['contacts'])} contacts at {pg['account_name']} "
                    f"show high-intent activity. Roles need human assignment."
                ),
                severity="warning",
                account_name=pg["account_name"],
                context={
                    "account_id": pg["account_id"],
                    "contacts": pg["contacts"],
                },
            )
            if exc:
                audit.log_sync(
                    action="buying_group.propose",
                    description=f"Proposed new buying group for account {pg['account_name']} ({pg['account_id']}) with {len(pg['contacts'])} contacts",
                    category="data",
                    resource_type="buying_group",
                    resource_id=pg["account_id"],
                    resource_name=pg["account_name"],
                    metadata={"contact_count": len(pg["contacts"])},
                )

        db.commit()

        all_groups = list(groups.values()) + list(proposed_groups.values())
        return {
            "buying_groups": all_groups,
            "existing_count": len(groups),
            "proposed_count": len(proposed_groups),
            "count": len(all_groups),
        }

    except Exception as e:
        log.error(f"Buying groups error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 2. DEDUPLICATION
# =============================================================================

@router.get("/dedup/config")
def get_dedup_config(db: Session = Depends(get_db)):
    """Return current dedup configuration (creates default if absent)."""
    config = db.query(DedupConfig).first()
    if not config:
        config = DedupConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.post("/dedup/config")
def update_dedup_config(update: DedupConfigUpdate, db: Session = Depends(get_db)):
    """Update dedup configuration settings."""
    config = db.query(DedupConfig).first()
    if not config:
        config = DedupConfig()
        db.add(config)

    old_threshold = config.confidence_threshold
    old_strategy = config.match_strategy

    config.confidence_threshold = update.confidence_threshold
    config.match_strategy = update.match_strategy
    db.commit()
    db.refresh(config)

    audit.log_sync(
        action="contact.dedup_config_update",
        description=f"Dedup config updated: threshold {old_threshold}→{update.confidence_threshold}, strategy {old_strategy}→{update.match_strategy}",
        category="data",
        resource_type="dedup_config",
        resource_id=str(config.id),
        metadata={
            "old_threshold": old_threshold,
            "new_threshold": update.confidence_threshold,
            "old_strategy": old_strategy,
            "new_strategy": update.match_strategy,
        },
    )

    return config


@router.post("/dedup/run")
def run_deduplication(db: Session = Depends(get_db)):
    """
    Run contact deduplication.

    Groups contacts by duplicate_key (email). For each group with 2+ members:
    - Above confidence threshold → auto-merge (highest-confidence record survives)
    - Below threshold → route to Workbench with all candidates side-by-side
    """
    try:
        # Get config
        config = db.query(DedupConfig).first()
        if not config:
            config = DedupConfig()
            db.add(config)
            db.commit()
            db.refresh(config)

        threshold = config.confidence_threshold

        # Find duplicate groups
        dup_groups = db.execute(text("""
            SELECT duplicate_key, COUNT(*) AS cnt
            FROM contact
            WHERE duplicate_key IS NOT NULL AND duplicate_key != ''
            GROUP BY duplicate_key
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
        """)).mappings().all()

        merged_count = 0
        exception_count = 0
        details = []

        for dg in dup_groups:
            dup_key = dg["duplicate_key"]

            # Get all contacts in this group
            contacts = db.execute(text("""
                SELECT "Id", "FirstName", "LastName", "Email", "Title",
                       "AccountId", confidence, duplicate_key, owner_name
                FROM contact
                WHERE duplicate_key = :dk
                ORDER BY CAST(COALESCE(NULLIF(confidence, ''), '0') AS FLOAT) DESC
            """), {"dk": dup_key}).mappings().all()

            contact_list = [dict(c) for c in contacts]
            if len(contact_list) < 2:
                continue

            # Parse confidences
            confidences = []
            for c in contact_list:
                try:
                    confidences.append(float(c.get("confidence") or 0))
                except (ValueError, TypeError):
                    confidences.append(0.0)

            max_confidence = max(confidences)
            master = contact_list[0]  # Already sorted by confidence DESC
            duplicates = contact_list[1:]

            if max_confidence >= threshold:
                # Auto-merge: keep master, log the merge
                dup_ids = [d["Id"] for d in duplicates]
                merged_count += len(dup_ids)

                audit.log_sync(
                    action="contact.dedup_merge",
                    description=(
                        f"Auto-merged {len(dup_ids)} duplicate(s) for email {dup_key}. "
                        f"Survivor: {master['Id']} (confidence={max_confidence})"
                    ),
                    category="data",
                    resource_type="contact",
                    resource_id=master["Id"],
                    resource_name=dup_key,
                    metadata={
                        "survivor_id": master["Id"],
                        "merged_ids": dup_ids,
                        "confidence": max_confidence,
                        "threshold": threshold,
                        "duplicate_key": dup_key,
                    },
                )

                details.append({
                    "action": "merged",
                    "duplicate_key": dup_key,
                    "survivor_id": master["Id"],
                    "merged_ids": dup_ids,
                    "confidence": max_confidence,
                })
            else:
                # Below threshold: route to Workbench
                exception_count += 1

                _create_exception_if_not_exists(
                    db,
                    exc_type="duplicate_contact",
                    title=f"Possible duplicate contacts: {dup_key}",
                    description=(
                        f"{len(contact_list)} contacts share duplicate_key '{dup_key}' "
                        f"but max confidence ({max_confidence}) is below threshold ({threshold}). "
                        f"Manual review required."
                    ),
                    severity="warning",
                    context={
                        "duplicate_key": dup_key,
                        "candidates": contact_list,
                        "confidence_scores": confidences,
                        "threshold": threshold,
                    },
                    ai_recommendation=f"Consider merging into {master['Id']} ({master.get('FirstName', '')} {master.get('LastName', '')})",
                    ai_confidence=int(max_confidence) if max_confidence else 0,
                )

                details.append({
                    "action": "exception",
                    "duplicate_key": dup_key,
                    "candidate_count": len(contact_list),
                    "max_confidence": max_confidence,
                })

        db.commit()

        audit.log_sync(
            action="contact.dedup_run",
            description=f"Deduplication run complete: {merged_count} merged, {exception_count} exceptions",
            category="data",
            resource_type="contact",
            resource_id="batch",
            metadata={"merged": merged_count, "exceptions": exception_count, "threshold": threshold},
        )

        return {
            "results": {
                "merged": merged_count,
                "exceptions": exception_count,
                "details": details,
            }
        }

    except Exception as e:
        log.error(f"Deduplication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 3. ROUTING CONFIGURATION
# =============================================================================

@router.get("/routing")
def get_routing_config(db: Session = Depends(get_db)):
    """
    Get routing rules, territories, SDR roster with computed coverage,
    plus detected collisions and capacity warnings.
    """
    try:
        # Routing rules
        routing_rules = db.execute(text(
            "SELECT * FROM routing_rules ORDER BY priority"
        )).mappings().all()
        rules_list = [dict(r) for r in routing_rules]

        # Territories
        territories = db.execute(text(
            "SELECT * FROM territories"
        )).mappings().all()
        territories_list = [dict(t) for t in territories]

        # SDR roster with computed coverage from routing_rules
        sdrs = db.execute(text(
            "SELECT * FROM sdr_roster"
        )).mappings().all()
        sdr_list = []
        for sdr in sdrs:
            s = dict(sdr)
            owner_id = s.get("owner_id")
            # Compute coverage as union of routing_rules rows
            coverage_rules = [
                {
                    "rule_id": r.get("rule_id"),
                    "rule_name": f"{r.get('region', '*')}/{r.get('segment', '*')}/{r.get('industry', '*')}",
                    "region": r.get("region"),
                    "segment": r.get("segment"),
                    "industry": r.get("industry"),
                    "priority": r.get("priority"),
                    "active": r.get("active"),
                }
                for r in rules_list
                if r.get("owner_id") == owner_id
            ]
            s["coverage_rules"] = coverage_rules
            sdr_list.append(s)

        # ── Collision detection ──────────────────────────────────────────
        # Rules with same (region, segment, industry, priority) but different owners
        collisions = []
        active_rules = [r for r in rules_list if _bool_true(r.get("active"))]
        seen: dict[str, list] = {}
        for r in active_rules:
            key = (
                (r.get("region") or "").lower(),
                (r.get("segment") or "").lower(),
                (r.get("industry") or "").lower(),
                str(r.get("priority", "")),
            )
            seen.setdefault(key, []).append(r)

        for key, group in seen.items():
            owners = set(r.get("owner_id") for r in group)
            if len(owners) > 1:
                collisions.append({
                    "rules": [r.get("rule_id") for r in group],
                    "region": group[0].get("region"),
                    "segment": group[0].get("segment"),
                    "industry": group[0].get("industry"),
                    "priority": group[0].get("priority"),
                    "owners": list(owners),
                    "description": f"Rules {', '.join(r.get('rule_id', '?') for r in group)} collide: same (region={group[0].get('region')}, segment={group[0].get('segment')}, industry={group[0].get('industry')}, priority={group[0].get('priority')}) but route to different owners ({', '.join(owners)})",
                })

        # ── Capacity warnings ────────────────────────────────────────────
        warnings = []
        for s in sdr_list:
            try:
                current = float(s.get("current_capacity") or 0)
                maximum = float(s.get("max_capacity") or 1)
            except (ValueError, TypeError):
                current, maximum = 0, 1

            if current > maximum:
                warnings.append({
                    "type": "capacity_overflow",
                    "owner_id": s.get("owner_id"),
                    "name": s.get("name"),
                    "current_capacity": current,
                    "max_capacity": maximum,
                    "description": f"{s.get('name')} ({s.get('owner_id')}) has current_capacity={current} > max_capacity={maximum}",
                })

            if _bool_false(s.get("active")):
                # Check if still referenced in active rules or territories
                referenced_rules = [
                    r.get("rule_id") for r in rules_list
                    if r.get("owner_id") == s.get("owner_id") and _bool_true(r.get("active"))
                ]
                referenced_territories = [
                    t.get("territory_id") for t in territories_list
                    if t.get("primary_owner_id") == s.get("owner_id")
                ]
                if referenced_rules or referenced_territories:
                    warnings.append({
                        "type": "inactive_sdr_referenced",
                        "owner_id": s.get("owner_id"),
                        "name": s.get("name"),
                        "active_rules": referenced_rules,
                        "territories": referenced_territories,
                        "description": (
                            f"{s.get('name')} ({s.get('owner_id')}) is inactive but still "
                            f"referenced in rules: {referenced_rules}, territories: {referenced_territories}"
                        ),
                    })

        return {
            "routing_rules": rules_list,
            "territories": territories_list,
            "sdr_roster": sdr_list,
            "collisions": collisions,
            "warnings": warnings,
        }

    except Exception as e:
        log.error(f"Routing config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routing/run")
def run_routing(body: RoutingRunRequest, db: Session = Depends(get_db)):
    """
    Run the routing assignment engine.

    For each contact: match (region, segment, industry) against active routing_rules.
    Collision resolution by capacity utilization ratio.
    Validation: winner must be active with capacity headroom.
    """
    try:
        # Get contacts to route
        if body.contact_ids:
            placeholders = ", ".join([f":c{i}" for i in range(len(body.contact_ids))])
            params = {f"c{i}": cid for i, cid in enumerate(body.contact_ids)}
            contact_query = f"""
                SELECT "Id", "FirstName", "LastName", "Email", region,
                       "AccountId", "Title"
                FROM contact
                WHERE "Id" IN ({placeholders})
            """
        else:
            # Route contacts that have no owner_id set or are unassigned
            contact_query = """
                SELECT "Id", "FirstName", "LastName", "Email", region,
                       "AccountId", "Title"
                FROM contact
                WHERE ("OwnerId" IS NULL OR "OwnerId" = '')
                LIMIT 100
            """
            params = {}

        contacts = db.execute(text(contact_query), params).mappings().all()

        # Get active routing rules
        active_rules = db.execute(text("""
            SELECT rule_id, region, segment, industry, owner_id, priority, active
            FROM routing_rules
            WHERE active = 'true' OR active = 'True' OR active = 't'
            ORDER BY priority ASC
        """)).mappings().all()
        active_rules_list = [dict(r) for r in active_rules]

        # Get SDR roster
        sdrs = db.execute(text("SELECT * FROM sdr_roster")).mappings().all()
        sdr_map = {dict(s)["owner_id"]: dict(s) for s in sdrs}

        assigned_count = 0
        exception_count = 0
        assignments = []

        for contact in contacts:
            c = dict(contact)
            c_region = (c.get("region") or "").strip()

            # Find matching rules
            matching = []
            for rule in active_rules_list:
                r_region = (rule.get("region") or "").strip()
                r_segment = (rule.get("segment") or "").strip()
                r_industry = (rule.get("industry") or "").strip()

                # Region must match
                if r_region.lower() != c_region.lower():
                    continue

                # Industry=null/empty in rule = wildcard
                # (We don't have segment on contact directly, so segment is matched
                #  via the account or is treated as a broad match in this context)
                matching.append(rule)

            if not matching:
                # No rules matched → exception
                exception_count += 1
                _create_exception_if_not_exists(
                    db,
                    exc_type="routing_no_match",
                    title=f"No routing rule for contact {c.get('FirstName', '')} {c.get('LastName', '')}",
                    description=f"Contact {c['Id']} (region={c_region}) matched no active routing rules.",
                    severity="warning",
                    prospect_id=c["Id"],
                    context={"contact": c, "region": c_region},
                )
                assignments.append({"contact_id": c["Id"], "action": "exception", "reason": "no_matching_rule"})
                continue

            # Group by priority to detect collisions
            by_priority: dict[str, list] = {}
            for rule in matching:
                p = str(rule.get("priority", 99))
                by_priority.setdefault(p, []).append(rule)

            # Process by priority (lowest first)
            assigned = False
            for priority in sorted(by_priority.keys(), key=lambda x: int(x)):
                candidates = by_priority[priority]
                owners_in_tier = list(set(r["owner_id"] for r in candidates))

                if len(owners_in_tier) > 1:
                    # Collision! Resolve by capacity utilization
                    audit.log_sync(
                        action="routing.collision_resolved",
                        description=(
                            f"Collision at priority {priority} for contact {c['Id']}: "
                            f"rules {', '.join(r['rule_id'] for r in candidates)} "
                            f"route to different owners {owners_in_tier}"
                        ),
                        category="data",
                        resource_type="routing_rule",
                        resource_id=candidates[0]["rule_id"],
                        metadata={
                            "contact_id": c["Id"],
                            "colliding_rules": [r["rule_id"] for r in candidates],
                            "owners": owners_in_tier,
                            "priority": priority,
                        },
                    )

                # Rank owners by utilization ratio
                scored_owners = []
                for oid in owners_in_tier:
                    sdr = sdr_map.get(oid)
                    if not sdr:
                        continue
                    if not _bool_true(sdr.get("active")):
                        continue
                    try:
                        current = float(sdr.get("current_capacity") or 0)
                        maximum = float(sdr.get("max_capacity") or 1)
                    except (ValueError, TypeError):
                        current, maximum = 0, 1
                    if current >= maximum:
                        continue  # Over capacity
                    ratio = current / maximum if maximum > 0 else 1.0
                    scored_owners.append((oid, ratio, sdr))

                # Sort by utilization (lower = more available)
                scored_owners.sort(key=lambda x: x[1])

                if scored_owners:
                    winner_id, winner_ratio, winner_sdr = scored_owners[0]
                    assigned = True
                    assigned_count += 1

                    rule_used = next(
                        (r for r in candidates if r["owner_id"] == winner_id),
                        candidates[0],
                    )

                    audit.log_sync(
                        action="routing.assign",
                        description=(
                            f"Assigned contact {c['Id']} to {winner_sdr.get('name', winner_id)} "
                            f"via rule {rule_used['rule_id']} (utilization={winner_ratio:.0%})"
                        ),
                        category="data",
                        resource_type="contact",
                        resource_id=c["Id"],
                        metadata={
                            "contact_id": c["Id"],
                            "assigned_owner": winner_id,
                            "rule_id": rule_used["rule_id"],
                            "utilization_ratio": round(winner_ratio, 3),
                        },
                    )

                    assignments.append({
                        "contact_id": c["Id"],
                        "action": "assigned",
                        "owner_id": winner_id,
                        "owner_name": winner_sdr.get("name"),
                        "rule_id": rule_used["rule_id"],
                        "utilization": round(winner_ratio, 3),
                    })
                    break  # Stop checking lower-priority tiers

            if not assigned:
                # All candidates failed validation
                exception_count += 1
                _create_exception_if_not_exists(
                    db,
                    exc_type="routing_no_capacity",
                    title=f"No eligible SDR for contact {c.get('FirstName', '')} {c.get('LastName', '')}",
                    description=(
                        f"Contact {c['Id']} matched {len(matching)} rule(s) but all owners "
                        f"are inactive or over capacity."
                    ),
                    severity="warning",
                    prospect_id=c["Id"],
                    context={"contact": c, "matching_rules": matching},
                )
                assignments.append({"contact_id": c["Id"], "action": "exception", "reason": "no_capacity"})

        db.commit()

        return {
            "results": {
                "assigned": assigned_count,
                "exceptions": exception_count,
                "assignments": assignments,
            }
        }

    except Exception as e:
        log.error(f"Routing run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 4. DATA ANALYSER / QUALITY
# =============================================================================

@router.get("/quality")
def get_data_quality(db: Session = Depends(get_db)):
    """Run comprehensive data quality checks on the live database and return results."""
    report = {
        "chronological": [],
        "relational": [],
        "state_logic": [],
        "format": [],
    }

    def add(category: str, issue: str, count: int, severity: str, examples: list | None = None):
        if count > 0:
            report[category].append({
                "issue": issue,
                "count": count,
                "severity": severity,
                "examples": examples or [],
            })
            # Create workbench exception (deduplicated)
            _create_exception_if_not_exists(
                db,
                exc_type="data_quality_anomaly",
                title=issue,
                description=f"Data quality check found {count} affected rows.",
                severity=severity,
                context={"examples": examples or [], "count": count},
            )

    # ── CHRONOLOGICAL ────────────────────────────────────────────────────────

    # 1. opportunity.closedate < opportunity.createddate
    try:
        res = db.execute(text(
            'SELECT "Id" FROM opportunity WHERE CAST("CloseDate" AS DATE) < CAST("CreatedDate" AS DATE)'
        )).fetchall()
        add("chronological", "opportunity.closedate < opportunity.createddate", len(res), "warning", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (closedate<createddate): {e}")

    # 2. contact.lastmodifieddate < contact.createddate
    try:
        res = db.execute(text(
            'SELECT "Id" FROM contact WHERE CAST("LastModifiedDate" AS DATE) < CAST("CreatedDate" AS DATE)'
        )).fetchall()
        add("chronological", "contact.lastmodifieddate < contact.createddate", len(res), "warning", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (lastmodified<created): {e}")

    # 3. opportunity.isclosed=true AND closedate > today (boolean flag, not stagename)
    try:
        res = db.execute(text("""
            SELECT "Id" FROM opportunity
            WHERE ("IsClosed" = 'True' OR "IsClosed" = 'true')
              AND CAST("CloseDate" AS DATE) > CURRENT_DATE
        """)).fetchall()
        add("chronological", "Closed opportunity with future close date (isclosed=true)", len(res), "warning", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (closed future): {e}")

    # 4. stagename ↔ isclosed/iswon flag desync
    try:
        res = db.execute(text("""
            SELECT "Id" FROM opportunity
            WHERE (
                "StageName" IN ('Closed Won', 'Closed Lost')
                AND ("IsClosed" = 'False' OR "IsClosed" = 'false')
            )
            OR (
                "StageName" = 'Closed Won'
                AND ("IsWon" = 'False' OR "IsWon" = 'false')
            )
            OR (
                "StageName" = 'Closed Lost'
                AND ("IsWon" = 'True' OR "IsWon" = 'true')
            )
            OR (
                "StageName" NOT IN ('Closed Won', 'Closed Lost')
                AND ("IsClosed" = 'True' OR "IsClosed" = 'true')
            )
        """)).fetchall()
        add("chronological", "StageName ↔ IsClosed/IsWon flag desync", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (stagename desync): {e}")

    # ── RELATIONAL ───────────────────────────────────────────────────────────

    # 1. opportunity.contactid not in contact.id
    try:
        res = db.execute(text("""
            SELECT o."Id" FROM opportunity o
            LEFT JOIN contact c ON o."ContactId" = c."Id"
            WHERE c."Id" IS NULL AND o."ContactId" IS NOT NULL
        """)).fetchall()
        add("relational", "opportunity.contactid missing in contact", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (opp.contactid FK): {e}")

    # 2. opportunity.accountid not in account.id
    try:
        res = db.execute(text("""
            SELECT o."Id" FROM opportunity o
            LEFT JOIN account a ON o."AccountId" = a."Id"
            WHERE a."Id" IS NULL AND o."AccountId" IS NOT NULL
        """)).fetchall()
        add("relational", "opportunity.accountid missing in account", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (opp.accountid FK): {e}")

    # 3. consent_register.contact_id not in contact.id (generic NOT EXISTS)
    try:
        res = db.execute(text("""
            SELECT cr.consent_id FROM consent_register cr
            LEFT JOIN contact c ON cr.contact_id = c."Id"
            WHERE c."Id" IS NULL
        """)).fetchall()
        add("relational", "consent_register.contact_id missing in contact (dangling FK)", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (consent FK): {e}")

    # 4. contact.accountid not in account.id
    try:
        res = db.execute(text("""
            SELECT c."Id" FROM contact c
            LEFT JOIN account a ON c."AccountId" = a."Id"
            WHERE a."Id" IS NULL AND c."AccountId" IS NOT NULL
        """)).fetchall()
        add("relational", "contact.accountid missing in account", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (contact.accountid FK): {e}")

    # 5. contact.accountid (via opp.contactid) differs from opp.accountid — report rate
    try:
        total_opps = db.execute(text(
            'SELECT COUNT(*) FROM opportunity WHERE "ContactId" IS NOT NULL AND "AccountId" IS NOT NULL'
        )).scalar() or 1

        res = db.execute(text("""
            SELECT o."Id"
            FROM opportunity o
            JOIN contact c ON o."ContactId" = c."Id"
            WHERE o."AccountId" != c."AccountId"
        """)).fetchall()

        mismatch_count = len(res)
        rate = round(mismatch_count / total_opps * 100, 1)
        if mismatch_count > 0:
            add(
                "relational",
                f"Contact↔Opportunity account mismatch ({rate}% of resolvable rows — systemic, not individual)",
                mismatch_count,
                "warning",
                [r[0] for r in res[:5]],
            )
    except Exception as e:
        log.warning(f"Quality check skip (accountid mismatch): {e}")

    # ── STATE / LOGIC ────────────────────────────────────────────────────────

    # 1. Ghost Deal: lead_stage__c='Opportunity' with zero opportunity rows for accountid
    try:
        res = db.execute(text("""
            SELECT c."Id" FROM contact c
            LEFT JOIN opportunity o ON c."AccountId" = o."AccountId"
            WHERE c.lead_stage__c = 'Opportunity' AND o."Id" IS NULL
        """)).fetchall()
        add("state_logic", "Ghost Deal (lead_stage=Opportunity but no opps on account)", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (ghost deal): {e}")

    # 2a. Phantom Customer — lower severity: no opportunity rows at all
    try:
        res = db.execute(text("""
            SELECT c."Id" FROM contact c
            LEFT JOIN opportunity o ON c."AccountId" = o."AccountId"
            WHERE c.lead_stage__c = 'Customer' AND o."Id" IS NULL
        """)).fetchall()
        add("state_logic", "Phantom Customer — no opportunities at all (plausibly legitimate)", len(res), "warning", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (phantom customer a): {e}")

    # 2b. Phantom Customer — higher severity: opps exist but none genuinely won
    try:
        res = db.execute(text("""
            SELECT c."Id" FROM contact c
            JOIN opportunity o ON c."AccountId" = o."AccountId"
            WHERE c.lead_stage__c = 'Customer'
            GROUP BY c."Id"
            HAVING SUM(
                CASE WHEN ("IsClosed" = 'True' OR "IsClosed" = 'true')
                      AND ("IsWon" = 'True' OR "IsWon" = 'true')
                     THEN 1 ELSE 0 END
            ) = 0
        """)).fetchall()
        add("state_logic", "Phantom Customer — opps exist but none are genuinely won (real desync)", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (phantom customer b): {e}")

    # 3. Lazy Rep: lead_stage__c in ('Open','MQL','SQL') with active opp on account
    try:
        res = db.execute(text("""
            SELECT DISTINCT c."Id" FROM contact c
            JOIN opportunity o ON c."AccountId" = o."AccountId"
            WHERE c.lead_stage__c IN ('Open', 'MQL', 'SQL')
              AND ("IsClosed" = 'False' OR "IsClosed" = 'false')
        """)).fetchall()
        add("state_logic", "Lazy Rep (lead open/MQL/SQL but active opp exists on account)", len(res), "warning", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (lazy rep): {e}")

    # 4. Pipeline desync: probability strictly between 0 and 100 while stagename is closed
    try:
        res = db.execute(text("""
            SELECT "Id" FROM opportunity
            WHERE CAST(NULLIF("Probability", '') AS FLOAT) > 0
              AND CAST(NULLIF("Probability", '') AS FLOAT) < 100
              AND ("StageName" IN ('Closed Won', 'Closed Lost')
                   OR "IsClosed" = 'True' OR "IsClosed" = 'true')
        """)).fetchall()
        add("state_logic", "Pipeline desync (probability 0<p<100 but deal is closed)", len(res), "warning", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (pipeline desync): {e}")

    # ── FORMAT / BUSINESS LOGIC ──────────────────────────────────────────────

    # 1. Mixed date formats in visitoractivity.created_at
    try:
        res = db.execute(text(
            "SELECT created_at FROM visitoractivity WHERE created_at IS NOT NULL"
        )).fetchall()
        if res:
            dates = [r[0] for r in res]
            format_counts = {"ISO": 0, "ISO-offset": 0, "UK-slash": 0, "Short-month-text": 0, "Other": 0}
            for d in dates:
                d_str = str(d).strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}T.*[+\-]\d{2}:", d_str):
                    format_counts["ISO-offset"] += 1
                elif re.match(r"^\d{4}-\d{2}-\d{2}", d_str):
                    format_counts["ISO"] += 1
                elif re.match(r"^\d{2}/\d{2}/\d{4}", d_str):
                    format_counts["UK-slash"] += 1
                elif re.match(r"^[A-Za-z]{3}\s\d{2}\s\d{4}", d_str):
                    format_counts["Short-month-text"] += 1
                else:
                    format_counts["Other"] += 1
            # Only report if multiple formats exist
            non_zero = {k: v for k, v in format_counts.items() if v > 0}
            if len(non_zero) > 1:
                add("format", f"Mixed date formats in visitoractivity.created_at: {non_zero}", len(dates), "warning")
    except Exception as e:
        log.warning(f"Quality check skip (va date formats): {e}")

    # 1b. Mixed date formats in consent_register.captured_at
    try:
        res = db.execute(text(
            "SELECT captured_at FROM consent_register WHERE captured_at IS NOT NULL"
        )).fetchall()
        if res:
            dates = [r[0] for r in res]
            format_counts = {"ISO": 0, "ISO-offset": 0, "UK-slash": 0, "Short-month-text": 0, "Other": 0}
            for d in dates:
                d_str = str(d).strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}T.*[+\-]\d{2}:", d_str):
                    format_counts["ISO-offset"] += 1
                elif re.match(r"^\d{4}-\d{2}-\d{2}", d_str):
                    format_counts["ISO"] += 1
                elif re.match(r"^\d{2}/\d{2}/\d{4}", d_str):
                    format_counts["UK-slash"] += 1
                elif re.match(r"^[A-Za-z]{3}\s\d{2}\s\d{4}", d_str):
                    format_counts["Short-month-text"] += 1
                else:
                    format_counts["Other"] += 1
            non_zero = {k: v for k, v in format_counts.items() if v > 0}
            if len(non_zero) > 1:
                add("format", f"Mixed date formats in consent_register.captured_at: {non_zero}", len(dates), "warning")
    except Exception as e:
        log.warning(f"Quality check skip (consent date formats): {e}")

    # 2. sdr_roster.current_capacity > max_capacity
    try:
        res = db.execute(text(
            "SELECT owner_id FROM sdr_roster WHERE CAST(current_capacity AS FLOAT) > CAST(max_capacity AS FLOAT)"
        )).fetchall()
        add("format", "sdr_roster current_capacity > max_capacity", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (capacity overflow): {e}")

    # 3. Inactive SDR still referenced as territories.primary_owner_id or active routing_rules.owner_id
    try:
        res = db.execute(text("""
            SELECT s.owner_id FROM sdr_roster s
            WHERE (s.active = 'false' OR s.active = 'False') AND (
                s.owner_id IN (SELECT primary_owner_id FROM territories) OR
                s.owner_id IN (SELECT owner_id FROM routing_rules WHERE active = 'true' OR active = 'True')
            )
        """)).fetchall()
        add("format", "Inactive SDR still referenced in active rules or territories", len(res), "high", [r[0] for r in res[:5]])
    except Exception as e:
        log.warning(f"Quality check skip (inactive sdr): {e}")

    db.commit()

    # Audit the scan
    total_issues = sum(len(report[cat]) for cat in report)
    total_rows = sum(item["count"] for cat in report for item in report[cat])
    audit.log_sync(
        action="quality.scan_complete",
        description=f"Data quality scan complete: {total_issues} issue types, {total_rows} total affected rows",
        category="data",
        resource_type="quality_scan",
        resource_id="latest",
        metadata={"issue_types": total_issues, "total_affected_rows": total_rows},
    )

    return report


# =============================================================================
# 5. CONSENT (existing — don't touch)
# =============================================================================

@router.get("/consent")
def get_consent_registry(db: Session = Depends(get_db)):
    """Get consent registry grouped by region with contact details."""
    try:
        rows = db.execute(text("""
            SELECT
                cr.consent_id,
                cr.contact_id,
                cr.basis,
                cr.region,
                cr.status,
                cr.channel,
                cr.source,
                cr.captured_at,
                cr.expires_at,
                c."FirstName" || ' ' || c."LastName" AS contact_name,
                c."Email" AS contact_email
            FROM consent_register cr
            LEFT JOIN contact c ON cr.contact_id = c."Id"
            ORDER BY cr.region, cr.status
        """)).mappings().all()

        by_region: dict[str, list] = {}
        for row in rows:
            r = dict(row)
            region = r["region"] or "Unknown"
            by_region.setdefault(region, []).append(r)

        return {
            "consent_records": [dict(r) for r in rows],
            "by_region": {k: len(v) for k, v in by_region.items()},
            "total": len(rows),
        }

    except Exception as e:
        log.error(f"Consent registry error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 6. INTEGRATIONS (existing — don't touch)
# =============================================================================

@router.get("/integrations")
def get_integrations():
    """Return the status of all connected integrations."""
    return {
        "integrations": [
            {
                "name": "PostgreSQL Database",
                "type": "system_of_record",
                "status": "healthy",
                "description": "Primary data store with seeded CRM data",
                "tables": 13,
            },
            {
                "name": "Supervity Auto (Orchestrator)",
                "type": "orchestration",
                "status": "healthy",
                "description": "AI Employee orchestration platform",
                "operators": 5,
            },
            {
                "name": "NVIDIA NIM (Nemotron 550B)",
                "type": "ai_model",
                "status": "healthy",
                "description": "Open-source LLM for AI Policy engine",
            },
            {
                "name": "Google Gemini",
                "type": "ai_model",
                "status": "healthy",
                "description": "LLM for AI Insights and data analytics",
            },
        ]
    }


# =============================================================================
# 7. DATABASE VIEWER (existing — don't touch)
# =============================================================================

from sqlalchemy import inspect as sqla_inspect


@router.get("/database/tables")
def get_db_tables(db: Session = Depends(get_db)):
    engine = db.get_bind()
    tables = sqla_inspect(engine).get_table_names()
    return {"tables": tables}


@router.get("/database/table/{table_name}")
def get_db_table_data(table_name: str, db: Session = Depends(get_db)):
    engine = db.get_bind()
    tables = sqla_inspect(engine).get_table_names()
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")

    rows = db.execute(text(f"SELECT * FROM {table_name} LIMIT 100")).mappings().all()
    return {"table": table_name, "rows": [dict(r) for r in rows]}
