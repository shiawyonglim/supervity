# app/services/bundler.py
"""
Data Enrichment & Bundler Service
Responsible for pulling VisitorActivity, joining with Contact/Account/Opportunity data,
and posting the rich payload to the Supervity Visual Workflow platform.
"""

import logging
import requests
from typing import List, Dict, Any
from sqlalchemy import text
from ..core.database import engine

log = logging.getLogger(__name__)

# TODO: Replace with the actual Supervity webhook URL
SUPERVITY_WEBHOOK_URL = "https://hook.supervity.com/your-endpoint-here"

def get_visitor_activities(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch raw visitor activities from the database."""
    with engine.connect() as conn:
        query = text("""
            SELECT id, visitor_id, prospect_id, type, created_at, url, duration_seconds, campaign, channel
            FROM visitoractivity
            WHERE prospect_id IS NOT NULL AND prospect_id != ''
            LIMIT :limit
        """)
        result = conn.execute(query, {"limit": limit})
        return [dict(row._mapping) for row in result]

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

def bundle_and_push_data(limit: int = 10):
    """
    Main job: Read visitor activities, join related data, and push to Supervity.
    """
    log.info(f"Starting Data Bundler Job (Limit: {limit})...")
    activities = get_visitor_activities(limit)
    
    bundled_payloads = []
    
    for activity in activities:
        prospect_id = activity.get("prospect_id")
        if not prospect_id:
            continue
            
        # Enrich the activity with all related CRM data
        enrichment = get_prospect_details(prospect_id)
        
        bundle = {
            "activity_id": activity.get("id"),
            "visitor_id": activity.get("visitor_id"),
            "prospect_id": prospect_id,
            "activity": {
                "type": activity.get("type"),
                "url": activity.get("url"),
                "duration_seconds": activity.get("duration_seconds"),
                "campaign": activity.get("campaign"),
                "channel": activity.get("channel")
            },
            "contact": enrichment.get("contact", {}),
            "account": enrichment.get("account", {}),
            "opportunities": enrichment.get("opportunities", [])
        }
        bundled_payloads.append(bundle)
        
    log.info(f"Successfully bundled {len(bundled_payloads)} records.")
    
    # Push to Supervity Workflow
    try:
        # We send the entire array to Supervity in one POST request
        # Supervity's Loop node will handle iterating through the array.
        log.info(f"Pushing payload to Supervity Webhook: {SUPERVITY_WEBHOOK_URL}")
        # response = requests.post(SUPERVITY_WEBHOOK_URL, json={"data": bundled_payloads})
        # response.raise_for_status()
        log.info("Push successful (Mocked).")
    except Exception as e:
        log.error(f"Failed to push to Supervity: {e}")
        
    return {"status": "success", "processed": len(bundled_payloads), "data": bundled_payloads}
