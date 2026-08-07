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

log = logging.getLogger(__name__)

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
        files = {
            "workflowId": (None, workflow_id),
            "inputs[lead_payload]": (None, json.dumps(payload))
        }
        
        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            
            log.info("--- Supervity Auto triggered successfully ---")
            return response.json()
            
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
