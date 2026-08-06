# app/services/operators.py
"""
AI Operators for processing Supervity leads.
"""

import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

# Core context that is passed between operators
class LeadContext:
    def __init__(self, raw_data: Dict[str, Any]):
        self.lead_id: str = raw_data.get("lead_id", "")
        self.name: str = raw_data.get("name", "")
        self.email: str = raw_data.get("email", "")
        self.company: str = raw_data.get("company", "")
        self.inquiry_text: str = raw_data.get("inquiry_text", "")
        self.source: str = raw_data.get("source", "")
        
        # State populated by operators
        self.is_valid: bool = False
        self.missing_fields: List[str] = []
        
        self.intent_score: float = 0.0
        self.intent_category: str = ""
        self.urgency: str = ""
        
        self.is_compliant: bool = False
        self.privacy_flags: List[str] = []
        
        self.email_subject: str = ""
        self.email_body: str = ""
        self.sent_status: bool = False
        
        self.slack_report: str = ""

def operator_a_validate(raw_payload: Dict[str, Any]) -> LeadContext:
    """Operator A: Data Reader & Validator"""
    log.info(f"Operator A: Validating payload for lead {raw_payload.get('lead_id')}")
    ctx = LeadContext(raw_payload)
    
    # Check for missing required fields
    required = ["email", "inquiry_text"]
    for req in required:
        if not raw_payload.get(req):
            ctx.missing_fields.append(req)
            
    if ctx.missing_fields:
        ctx.is_valid = False
        log.warning(f"Operator A: Missing fields {ctx.missing_fields}. Pinging Slack.")
        # TODO: Ping Slack here
    else:
        ctx.is_valid = True
        
    return ctx

def operator_b_score_intent(ctx: LeadContext) -> LeadContext:
    """Operator B: Intent Scorer"""
    if not ctx.is_valid:
        return ctx
        
    log.info(f"Operator B: Scoring intent for {ctx.lead_id}")
    # TODO: Implement LLM call here (e.g., llm.gemini_json)
    
    # Mocking response for now
    ctx.intent_score = 0.95
    ctx.intent_category = "Purchase Ready"
    ctx.urgency = "High"
    return ctx

def operator_c_check_privacy(ctx: LeadContext) -> LeadContext:
    """Operator C: Privacy Law Checker"""
    if not ctx.is_valid:
        return ctx
        
    log.info(f"Operator C: Checking privacy for {ctx.lead_id}")
    # TODO: Implement LLM/Rule check for GDPR and PII
    
    ctx.is_compliant = True
    ctx.privacy_flags = ["GDPR Region Detected (EU)"]
    return ctx

def operator_d_draft_email(ctx: LeadContext) -> LeadContext:
    """Operator D: Email Drafter & Sender"""
    if not ctx.is_valid or not ctx.is_compliant:
        return ctx
        
    log.info(f"Operator D: Drafting email for {ctx.lead_id}")
    # TODO: Implement LLM draft generation and SMTP send
    
    ctx.email_subject = f"Enterprise Hosting in the EU for {ctx.company}"
    ctx.email_body = "Hello, ..."
    ctx.sent_status = True
    return ctx

def operator_e_report(ctx: LeadContext) -> LeadContext:
    """Operator E: Reporting & Slack Notification"""
    if not ctx.is_valid:
        ctx.slack_report = f"Failed to process lead {ctx.lead_id}. Missing fields: {ctx.missing_fields}"
    else:
        ctx.slack_report = f"✅ High-intent lead {ctx.name} processed. Privacy checks passed. Welcome email sent."
        
    log.info(f"Operator E: Sending report to Slack -> {ctx.slack_report}")
    # TODO: Send slack webhook
    return ctx

def push_to_supervity(prospect_data: Dict[str, Any]) -> None:
    """Mock pushing the final data to the external Supervity platform."""
    log.info(f"Pushing data to Supervity API for {prospect_data.get('prospect_id')}")
    # TODO: requests.post("https://api.supervity.com/update-lead", json=prospect_data)

def run_operator_pipeline_batch(raw_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Runs all 5 operators sequentially across a batch of prospects."""
    results = []
    
    for raw_payload in raw_payloads:
        log.info(f"--- Processing Prospect {raw_payload.get('lead_id')} ---")
        ctx = operator_a_validate(raw_payload)
        ctx = operator_b_score_intent(ctx)
        ctx = operator_c_check_privacy(ctx)
        ctx = operator_d_draft_email(ctx)
        ctx = operator_e_report(ctx)
        
        final_data = {
            "prospect_id": ctx.lead_id,
            "ai_processed": True,
            "intent_score_assigned": ctx.intent_score,
            "privacy_cleared": ctx.is_compliant,
            "action_taken": "Email Sent" if ctx.sent_status else "Pipeline Halted",
            "summary": ctx.slack_report
        }
        results.append(final_data)
        
        # Push to Supervity immediately
        push_to_supervity(final_data)
        
    return results
