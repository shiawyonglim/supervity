# app/services/operators.py
"""
AI Operators for processing Supervity leads.
"""

import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

import json

# Core context that is passed between operators
class LeadContext:
    def __init__(self, raw_data: Dict[str, Any]):
        # Supervity often nests payloads or sends stringified JSON.
        # Let's cleanly extract the real data block.
        if "Lead Payload" in raw_data:
            raw_data = raw_data["Lead Payload"]
        elif "lead_payload" in raw_data:
            raw_data = raw_data["lead_payload"]
            
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except json.JSONDecodeError:
                log.error("Failed to parse stringified JSON payload")
                raw_data = {}

        self.raw_data = raw_data
        self.lead_id: str = raw_data.get("prospect_id", "")
        
        contact = raw_data.get("contact", {})
        self.name: str = contact.get("name", "")
        self.email: str = contact.get("email", "")
        
        # External inputs parsed directly from the single payload
        self.external_intent_score: float = raw_data.get("external_intent_score", 0.0)
        self.external_privacy_flag: bool = raw_data.get("external_privacy_flag", False)
        
        # Operator state
        self.missing_fields: List[str] = []
        self.internal_intent_score: float = 0.0
        self.requires_human_review: bool = False
        
        self.internal_privacy_flag: bool = False
        self.is_compliant: bool = False
        
        self.email_subject: str = ""
        self.email_body: str = ""
        self.sent_status: bool = False
        
        self.slack_report: str = ""


# ==========================================
# THE 5 OPERATORS
# ==========================================

def operator_1_intake(ctx: LeadContext) -> LeadContext:
    """Operator 1: Intake & Verification Operator"""
    log.info(f"[Op1] Validating payload for lead {ctx.lead_id}")
    
    required = ["email"]
    for req in required:
        if not getattr(ctx, req, None):
            ctx.missing_fields.append(req)
            
    if ctx.missing_fields:
        log.warning(f"[Op1] Missing fields {ctx.missing_fields}. Asking user via Slack.")
        # TODO: Trigger Slack integration to ask user for missing info
        
    return ctx

def operator_2_intent_scoring(ctx: LeadContext) -> LeadContext:
    """Operator 2: Intent Scoring Operator"""
    if ctx.missing_fields:
        return ctx
        
    log.info(f"[Op2] Double-checking intent score for {ctx.lead_id}")
    
    # Mocking internal calculation. In reality, this would be an LLM call.
    ctx.internal_intent_score = 0.85 
    
    # Double check if internal calculation matches external calculation (within threshold)
    delta = abs(ctx.internal_intent_score - ctx.external_intent_score)
    if delta > 0.1:
        log.warning(f"[Op2] Score mismatch! Internal: {ctx.internal_intent_score}, External: {ctx.external_intent_score}")
        ctx.requires_human_review = True
        # TODO: Trigger Slack integration to ask human to review the score
    else:
        log.info("[Op2] Intent score verified successfully.")
        
    return ctx

def operator_3_privacy_compliance(ctx: LeadContext) -> LeadContext:
    """Operator 3: Privacy Compliance Operator"""
    if ctx.missing_fields:
        return ctx
        
    log.info(f"[Op3] Double-checking privacy compliance for {ctx.lead_id}")
    
    # Mocking internal privacy check
    ctx.internal_privacy_flag = True
    
    if ctx.internal_privacy_flag == ctx.external_privacy_flag:
        ctx.is_compliant = ctx.internal_privacy_flag
        log.info(f"[Op3] Privacy compliance verified: {ctx.is_compliant}")
    else:
        log.error(f"[Op3] Privacy mismatch! Internal: {ctx.internal_privacy_flag}, External: {ctx.external_privacy_flag}")
        ctx.is_compliant = False
        ctx.requires_human_review = True
        
    return ctx

def operator_4_communication(ctx: LeadContext) -> LeadContext:
    """Operator 4: Communication Operator"""
    if ctx.missing_fields or ctx.requires_human_review or not ctx.is_compliant:
        log.info("[Op4] Skipping communication draft due to failed preconditions or pending human review.")
        return ctx
        
    log.info(f"[Op4] Drafting and sending email for {ctx.lead_id}")
    
    # Mocking email generation using the validated scores
    ctx.email_subject = f"Hello {ctx.name}, regarding your inquiry"
    ctx.email_body = f"Based on your high intent score ({ctx.external_intent_score}), we would like to offer..."
    ctx.sent_status = True
    
    return ctx

def operator_5_reporting(ctx: LeadContext) -> LeadContext:
    """Operator 5: Reporting Operator"""
    log.info(f"[Op5] Generating summary report for {ctx.lead_id}")
    
    if ctx.missing_fields:
        ctx.slack_report = f"⚠️ Halted processing for {ctx.lead_id}. Missing fields: {ctx.missing_fields}"
    elif ctx.requires_human_review:
        ctx.slack_report = f"⚠️ Halted processing for {ctx.lead_id}. Awaiting human review due to data discrepancies."
    elif not ctx.is_compliant:
        ctx.slack_report = f"🛑 Halted processing for {ctx.lead_id}. Failed privacy compliance."
    else:
        ctx.slack_report = f"✅ Success for {ctx.lead_id}. Verified external score ({ctx.external_intent_score}) and privacy flag. Email sent."
        
    log.info(f"[Op5] Sending Slack Report: {ctx.slack_report}")
    # TODO: Send slack webhook
    return ctx


# ==========================================
# MASTER ORCHESTRATOR
# ==========================================

class MasterOrchestrator:
    """
    Coordinates the entire workflow since Supervity cannot handle complex comparisons or 
    simple variable passing natively. 
    It receives the initial data AND the pre-calculated metrics from external systems,
    and passes them down the operator pipeline.
    """
    
    @staticmethod
    def process_lead(payload: Dict[str, Any]) -> Dict[str, Any]:
        log.info(f"--- Master Orchestrator starting for {payload.get('prospect_id')} ---")
        
        # Initialize Context (extracts everything from the single payload)
        ctx = LeadContext(payload)
        
        # Run Pipeline Sequentially
        ctx = operator_1_intake(ctx)
        ctx = operator_2_intent_scoring(ctx)
        ctx = operator_3_privacy_compliance(ctx)
        ctx = operator_4_communication(ctx)
        ctx = operator_5_reporting(ctx)
        
        # Compile final results
        final_data = {
            "prospect_id": ctx.lead_id,
            "missing_fields": ctx.missing_fields,
            "human_review_required": ctx.requires_human_review,
            "privacy_cleared": ctx.is_compliant,
            "action_taken": "Email Sent" if ctx.sent_status else "Pipeline Halted",
            "summary": ctx.slack_report
        }
        
        log.info("--- Master Orchestrator finished ---")
        return final_data

def run_operator_pipeline_batch(batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Legacy wrapper for batch processing using the new MasterOrchestrator"""
    results = []
    for payload in batch_data:
        res = MasterOrchestrator.process_lead(payload)
        results.append(res)
    return results
