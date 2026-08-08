# app/services/knowledge_base_seed.py
"""Seed default Knowledge Base reference documents (idempotent — only runs once)."""

import logging

from sqlalchemy.orm import Session

from ..models.knowledge_base import KnowledgeDocument

log = logging.getLogger(__name__)

DEFAULT_DOCUMENTS = [
    {
        "title": "ICP & Intent Scoring",
        "category": "reference",
        "content": (
            "Lead intent/qualification score = sum of matched attribute weights.\n"
            "Firmographic fit (0.00-0.60): Industry=Manufacturing (0.25) or Logistics (0.20), "
            "NumberOfEmployees>500 (0.20), BillingCountry=MY or SG (0.15 each), "
            "Title contains 'Head' (0.15) or 'VP' (0.20).\n"
            "Behavioral intent (0.00-0.75): url=/pricing (0.30) or /demo (0.25), "
            "duration_seconds>300 (0.20).\n"
            "Thresholds: score >= 0.70 = High-Intent -> route to sales / sequence SEQ-01 or SEQ-02. "
            "score 0.40-0.69 = Medium-Intent -> nurture cadence SEQ-04. "
            "score < 0.40 = Low-Intent -> retain in marketing pool."
        ),
    },
    {
        "title": "Consent & Privacy Compliance",
        "category": "reference",
        "content": (
            "Before ANY outreach action (email, call, or sequence touch), verify in order:\n"
            "1. Contact.HasOptedOutOfEmail must be false for email outreach.\n"
            "2. Contact.DoNotCall must be false for call outreach.\n"
            "3. Consent_Register must have an 'active' record for the contact covering the "
            "applicable region — if status is 'withdrawn' or 'expired', block outreach.\n"
            "4. Cross-region rule: a contact whose consent was captured under one region but who "
            "now operates under EU jurisdiction is subject to GDPR and requires explicit opt_in, "
            "not soft_opt_in or legitimate_interest.\n"
            "5. Consent must be re-checked before EVERY touch in a sequence, not just at enrollment — "
            "a contact can withdraw consent mid-sequence. If consent fails mid-sequence, stop sending "
            "remaining touches and do not auto-resume if consent is later restored; that is a fresh "
            "decision.\n"
            "Never guess a region if it is blank — escalate to the Workbench instead."
        ),
    },
    {
        "title": "Routing & SDR Capacity",
        "category": "reference",
        "content": (
            "Leads are routed via Routing_Rules (matched by region, segment, industry, priority) to "
            "SDR_Roster owners. If two active rules tie at the same priority for the same "
            "region/segment/industry, assign to the rep with the LOWEST current_capacity/max_capacity "
            "utilization ratio.\n"
            "If the target SDR's current_capacity >= max_capacity, do not assign — fall back to the "
            "secondary territory SDR, or if none is available, route the lead to the Workbench as a "
            "capacity-overflow exception.\n"
            "Strategic accounts (Account.Strategic__c = true) always bypass automated routing and "
            "sequence enrollment — assign directly to the account's existing OwnerId."
        ),
    },
    {
        "title": "Sequence Eligibility",
        "category": "reference",
        "content": (
            "Sequence eligibility is determined by Contact.lead_stage__c:\n"
            "Open -> SEQ-04 Trade-Show Nurture (4 touches, email, 4 days apart).\n"
            "MQL -> SEQ-01 Inbound High-Intent MY (5 touches, email, 2 days apart). "
            "(SEQ-05 also targets MQL but is INACTIVE — never match it.)\n"
            "SQL -> SEQ-02 Pricing-Page Fast Follow (3 touches, email, 1 day) AND SEQ-06 Enterprise "
            "Exec Outreach (5 touches, multi-channel, 3 days) both match — this is a collision. Do "
            "NOT auto-pick; escalate to the Workbench with both candidates and an AI-recommended pick, "
            "unless a priority rule has since been added to the sequence config.\n"
            "Opportunity -> SEQ-03 Buying-Group Account Play (6 touches, multi-channel, 3 days).\n"
            "Customer -> no sequence. Do not enroll, but surface these contacts as 'no eligible "
            "sequence' in reporting rather than silently dropping them."
        ),
    },
    {
        "title": "Buying Group & Duplicate Resolution",
        "category": "reference",
        "content": (
            "If 3+ contacts from the same Account are active (visiting, engaging) within the same "
            "week, treat them as a single Buying Group (see Buying_Group table) and run ONE "
            "account-based play (SEQ-03) instead of separate individual sequences per contact.\n"
            "For duplicate leads sharing the same normalized Contact.duplicate_key across sources, "
            "merge into a single master Contact, preserving full history and keeping the field values "
            "from the record with the highest confidence score.\n"
            "If a contact's Lead_Stage__c is already 'Opportunity' or an active Opportunity exists for "
            "them, do not create a duplicate lead — route any new inbound signal to the existing "
            "Opportunity's OwnerId instead."
        ),
    },
]


def seed_default_documents(db: Session) -> None:
    """Insert the default reference documents if the table is empty."""
    try:
        existing_count = db.query(KnowledgeDocument).count()
        if existing_count > 0:
            return

        for doc in DEFAULT_DOCUMENTS:
            db.add(KnowledgeDocument(**doc, source="seed"))
        db.commit()
        log.info(f"Seeded {len(DEFAULT_DOCUMENTS)} default knowledge base documents.")
    except Exception as e:
        log.error(f"Failed to seed knowledge base documents: {e}")
        db.rollback()
