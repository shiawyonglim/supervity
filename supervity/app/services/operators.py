# app/services/operators.py
"""
AI Operators for processing Supervity leads.
"""

import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

import logging
import os
import json
import requests
from typing import Dict, Any, List

from ..core.database import SessionLocal
from .knowledge_base import build_knowledge_base_text

log = logging.getLogger(__name__)


def _get_knowledge_base_text() -> str:
    """Fetch the current knowledge base text (active policies + reference docs) so every
    Auto trigger is grounded in whatever a business user most recently edited."""
    try:
        with SessionLocal() as db:
            return build_knowledge_base_text(db)
    except Exception as e:
        log.error(f"Failed to build knowledge base text for Auto trigger: {e}")
        return "(Knowledge base unavailable.)"


class MasterOrchestrator:
    """
    Coordinates the entire workflow by triggering the Supervity Auto Orchestrator workflow.
    """

    @staticmethod
    def process_lead(payload: Dict[str, Any]) -> Dict[str, Any]:
        log.info(f"--- Master Orchestrator triggering Supervity Auto for {payload.get('prospect_id')} ---")

        api_key = os.getenv("WORKFLOW_API_KEY")
        workflow_id = os.getenv("SUPERVITY_WORKFLOW_ID")
        
        if not api_key:
            log.error("WORKFLOW_API_KEY is not set. Cannot trigger Auto.")
            return {"error": "WORKFLOW_API_KEY missing"}
            
        if not workflow_id:
            log.warning("SUPERVITY_WORKFLOW_ID is not set. Simulating Auto trigger.")
            # For hackathon purposes, if the user hasn't put the ID in yet, we return a mock success
            # to prevent the app from crashing, but log heavily that they need to add it.
            return {
                "prospect_id": payload.get("prospect_id", "unknown"),
                "status": "simulated_success",
                "message": "Please add SUPERVITY_WORKFLOW_ID to .env to make real API call."
            }
            
        url = "https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "x-source": "external",
            "x-active-org": "R.E.P.O",
            "x-user-timezone": "Asia/Kuala_Lumpur"
        }
        
        # Supervity expects multipart/form-data for inputs
        # To guarantee it receives the payload, we'll send it in multiple formats
        payload_json = json.dumps(payload)
        payload_str = str(payload)

        # Ground the run in the live, business-editable Knowledge Base (active AI Policies +
        # reference docs). Any edit made in the Knowledge Base UI is picked up on the very
        # next trigger — no redeploy needed.
        knowledge_base_text = _get_knowledge_base_text()

        files = {
            "workflowId": (None, workflow_id, 'text/plain'),
            "inputs[lead_payload]": (None, payload_json, 'application/json'),      # Documented format (JSON string)
            "inputs[knowledge_base]": (None, knowledge_base_text, 'text/plain'),   # Live policies + reference docs
            "inputs": (None, json.dumps({"lead_payload": payload, "knowledge_base": knowledge_base_text}), 'application/json'), # Alternate nested format
            "lead_payload": (None, payload_json, 'application/json'),              # Direct field
            "payload": (None, payload_json, 'application/json'),                   # Generic field
            "knowledge_base": (None, knowledge_base_text, 'text/plain'),           # Direct field fallback
            "text": (None, payload_json, 'text/plain')                       # Some generic fallback
        }
        
        try:
            # We also send data instead of files just in case it wants urlencoded, but we'll stick to multipart as per docs
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            
            log.info("--- Supervity Auto triggered successfully ---")
            
            # Read response
            resp_data = response.json() if response.text else {}
            return resp_data
            
        except Exception as e:
            log.error(f"Failed to trigger Supervity Auto workflow: {e}")
            if hasattr(e, 'response') and e.response is not None:
                log.error(f"Response: {e.response.text}")
            return {"error": str(e)}

def run_operator_pipeline_batch(batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Wrapper for batch processing using the new MasterOrchestrator hitting the Auto platform."""
    results = []
    for payload in batch_data:
        res = MasterOrchestrator.process_lead(payload)
        results.append(res)
    return results
