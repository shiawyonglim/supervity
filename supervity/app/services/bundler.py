# app/services/bundler.py
"""
Data Enrichment & Bundler Service
Responsible for pulling VisitorActivity, joining with Contact/Account/Opportunity data,
and posting the rich payload to the Supervity Visual Workflow platform.
"""

import logging
import os
from typing import List, Dict, Any
from sqlalchemy import text
from supabase import create_client, Client
from ..core.database import engine, SessionLocal
from ..services.audit import audit, AuditCategory, AuditSeverity
from ..services.knowledge_base import build_knowledge_base_text
from ..routers.insights import generate_insights

log = logging.getLogger(__name__)

# Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    log.warning("Supabase credentials not found in environment variables.")

def get_visitor_activities(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch ALL visitor activities and apply forward-filling per visitor_id.
    
    Forward filling means: for a given visitor_id, if ANY row has a prospect_id,
    campaign, company_domain, or channel, we carry that value to all other rows
    for the same visitor that are missing those fields. This ensures no activity
    data is lost just because some rows have gaps.
    """
    with engine.connect() as conn:
        # Step 1: Fetch ALL activities (not just ones with prospect_id)
        query = text("""
            SELECT id, visitor_id, prospect_id, type, created_at, url,
                   duration_seconds, campaign, source, company_domain, channel
            FROM visitoractivity
            ORDER BY visitor_id, created_at
        """)
        result = conn.execute(query)
        all_activities = [dict(row._mapping) for row in result]
    
    # Step 2: Group activities by visitor_id
    visitor_groups: Dict[str, List[Dict]] = {}
    for act in all_activities:
        vid = str(act.get("visitor_id", ""))
        if vid not in visitor_groups:
            visitor_groups[vid] = []
        visitor_groups[vid].append(act)
    
    # Step 3: Forward-fill missing fields within each visitor group
    fill_fields = ["prospect_id", "campaign", "company_domain", "channel"]
    
    for vid, activities in visitor_groups.items():
        # First pass: find the known values for this visitor
        known_values = {}
        for field in fill_fields:
            for act in activities:
                val = act.get(field)
                if val and str(val).strip():
                    known_values[field] = val
                    break  # use the first non-empty value found
        
        # Second pass: fill in the blanks
        for act in activities:
            for field in fill_fields:
                current = act.get(field)
                if (not current or not str(current).strip()) and field in known_values:
                    act[field] = known_values[field]
    
    # Step 4: Flatten back and keep only rows that now have a prospect_id
    filled_activities = []
    for activities in visitor_groups.values():
        for act in activities:
            pid = act.get("prospect_id")
            if pid and str(pid).strip():
                filled_activities.append(act)
    
    # Apply limit after forward-fill
    return filled_activities[:limit]

def get_prospect_details(prospect_id: str) -> Dict[str, Any]:
    """Fetch contact, account, and opportunity details for a prospect."""
    details = {}
    with engine.connect() as conn:
        # Get Contact
        contact_query = text("""
            SELECT "FirstName", "LastName", "Email", "Title", "AccountId"
            FROM contact
            WHERE "Id" = :pid
            LIMIT 1
        """)
        contact_res = conn.execute(contact_query, {"pid": prospect_id}).first()
        
        if contact_res:
            c = dict(contact_res._mapping)
            details["contact"] = {
                "name": f"{c.get('FirstName', '')} {c.get('LastName', '')}".strip(),
                "email": c.get("Email"),
                "title": c.get("Title")
            }
            
            # Get Account
            account_id = c.get("AccountId")
            if account_id:
                account_query = text("""
                    SELECT "Name", "Industry", "NumberOfEmployees", "BillingCountry"
                    FROM account
                    WHERE "Id" = :aid
                    LIMIT 1
                """)
                acc_res = conn.execute(account_query, {"aid": account_id}).first()
                if acc_res:
                    details["account"] = dict(acc_res._mapping)
                    
            # Get Opportunities
            opp_query = text("""
                SELECT "Name", "StageName", "Amount", "IsClosed"
                FROM opportunity
                WHERE "AccountId" = :aid
            """)
            opp_res = conn.execute(opp_query, {"aid": account_id})
            details["opportunities"] = [dict(row._mapping) for row in opp_res]
            
    return details

def bundle_and_push_data(limit: int = 10, mode: str = "direct"):
    """
    Main job: Read visitor activities (with forward-filling), group by prospect,
    join related CRM data, and push to Supabase for Supervity to consume.
    mode can be 'direct' (full JSON to orchestrator) or 'supabase' (only IDs).
    """
    log.info(f"Starting Data Bundler Job (Limit: {limit}, Mode: {mode})...")
    activities = get_visitor_activities(limit)
    
    # Group all activities by prospect_id so each prospect gets ONE bundle
    prospect_activities: Dict[str, List[Dict]] = {}
    for activity in activities:
        pid = activity.get("prospect_id")
        if not pid:
            continue
        if pid not in prospect_activities:
            prospect_activities[pid] = []
        prospect_activities[pid].append(activity)
    
    bundled_payloads = []
    
    for prospect_id, acts in prospect_activities.items():
        # Enrich with CRM data (Contact, Account, Opportunity)
        enrichment = get_prospect_details(prospect_id)
        
        # Build the activities list for this prospect
        activity_list = []
        for act in acts:
            activity_list.append({
                "activity_id": act.get("id"),
                "type": act.get("type"),
                "url": act.get("url"),
                "duration_seconds": act.get("duration_seconds"),
                "campaign": act.get("campaign"),
                "channel": act.get("channel"),
                "source": act.get("source"),
                "company_domain": act.get("company_domain"),
            })
        
        bundle = {
            "prospect_id": prospect_id,
            "visitor_id": acts[0].get("visitor_id"),
            "contact": enrichment.get("contact", {}),
            "account": enrichment.get("account", {}),
            "opportunities": enrichment.get("opportunities", []),
            "activities": activity_list,
            "external_intent_score": 0.88,
            "external_privacy_flag": False
        }
        bundled_payloads.append(bundle)
        
    log.info(f"Successfully bundled {len(bundled_payloads)} prospects (from {len(activities)} activity rows).")
    
    # Push to Supabase Queue Table
    try:
        if not supabase:
            raise ValueError("Supabase client is not initialized.")
            
        log.info(f"Pushing {len(bundled_payloads)} records to Supabase 'supervity_queue' table...")
        
        # Prepare the payload array for Supabase insertion
        supabase_records = []
        for bundle in bundled_payloads:
            supabase_records.append({
                "prospect_id": bundle["prospect_id"],
                "payload": bundle,
                "status": "pending"
            })
            
        # Insert all records in one batch
        response = supabase.table("supervity_queue").insert(supabase_records).execute()
        log.info(f"Push successful! Inserted {len(response.data)} records into Supabase.")
        
        audit.log_sync(
            action="data.pushed",
            description=f"Pushed {len(response.data)} records to Supabase supervity_queue.",
            category=AuditCategory.DATA,
            severity=AuditSeverity.INFO,
            resource_type="data_bundle",
            metadata={"count": len(response.data), "prospect_ids": [b["prospect_id"] for b in bundled_payloads]},
            actor={"id": "system", "email": "bundler@supervity.ai"}
        )
        
        # Trigger Supervity Master Orchestrator Node
        if mode == "direct":
            for bundle in bundled_payloads:
                trigger_supervity_orchestrator(bundle=bundle, mode="direct")
        else:
            # supabase mode - send all IDs in one payload
            prospect_ids = [bundle["prospect_id"] for bundle in bundled_payloads]
            trigger_supervity_orchestrator(prospect_ids=prospect_ids, mode="supabase")
        
        # Generate Insights automatically
        generate_new_insights_in_background()
        
    except Exception as e:
        log.error(f"Failed to push to Supabase or trigger workflow: {e}")
        return {"status": "error", "message": str(e)}
        
    return {"status": "success", "processed": len(bundled_payloads), "data": bundled_payloads}

def generate_new_insights_in_background():
    """Generates insights automatically in the background using a local DB session."""
    import threading
    
    def _run_insights():
        try:
            log.info("Generating new AI Insights in background...")
            with SessionLocal() as db:
                generate_insights(db)
            log.info("Successfully generated and saved new AI Insights.")
        except Exception as e:
            log.error(f"Failed to generate AI Insights in background: {e}")
            
    # Run in a background thread to avoid blocking the bundler response
    threading.Thread(target=_run_insights, daemon=True).start()

def trigger_supervity_orchestrator(bundle: dict = None, prospect_ids: List[str] = None, mode: str = "direct"):
    import requests
    import json
    
    url = "https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream"
    api_key = os.getenv("WORKFLOW_API_KEY")
    
    if not api_key:
        log.error("WORKFLOW_API_KEY is not set. Cannot trigger orchestrator.")
        return
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-source": "external",
        "x-active-org": "R.E.P.O",
        "x-user-timezone": "Asia/Kuala_Lumpur"
    }
    
    if mode == "direct" and bundle:
        payload_to_send = bundle
        log_msg = f"Triggering Supervity Master Orchestrator Node (DIRECT) for prospect {bundle.get('prospect_id')}..."
        audit_desc = f"Triggered Master Orchestrator (Direct) for prospect {bundle.get('prospect_id')}."
        audit_meta = {"mode": mode, "prospect_id": bundle.get("prospect_id")}
    else:
        payload_to_send = {
            "status": "ready",
            "prospect_ids": prospect_ids,
            "count": len(prospect_ids) if prospect_ids else 0
        }
        log_msg = f"Triggering Supervity Master Orchestrator Node (SUPABASE) with {len(prospect_ids)} IDs..."
        audit_desc = f"Triggered Master Orchestrator (Supabase) with {len(prospect_ids)} IDs."
        audit_meta = {"mode": mode, "prospect_ids": prospect_ids}

    # Send the full bundle payload which contains 'contact', 'account', 'activities', etc.
    payload_str = json.dumps(payload_to_send)

    # Ground the run in the live, business-editable Knowledge Base (active AI Policies +
    # reference docs) so an edit made in the UI takes effect on the very next trigger.
    try:
        with SessionLocal() as kb_db:
            knowledge_base_text = build_knowledge_base_text(kb_db)
    except Exception as e:
        log.error(f"Failed to build knowledge base text for Auto trigger: {e}")
        knowledge_base_text = "(Knowledge base unavailable.)"

    files = {
        "workflowId": (None, "019fd5dd-4f56-7000-8641-9bfdd6c1e3e1"),
        "inputs[lead_payload]": (None, payload_str),
        "inputs[knowledge_base]": (None, knowledge_base_text),
    }
    
    try:
        log.info(log_msg)
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        log.info(f"Successfully triggered orchestrator. Response: {response.status_code}")
        
        audit.log_sync(
            action="orchestrator.triggered",
            description=audit_desc,
            category=AuditCategory.SYSTEM,
            severity=AuditSeverity.INFO,
            resource_type="workflow",
            metadata={"status_code": response.status_code, **audit_meta},
            actor={"id": "system", "email": "bundler@supervity.ai"}
        )
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to trigger orchestrator: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log.error(f"Response details: {e.response.text}")
