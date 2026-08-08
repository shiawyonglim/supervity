# app/services/operators.py
"""
AI Operators for processing Supervity leads.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..core.database import SessionLocal
from .knowledge_base import build_knowledge_base_text

log = logging.getLogger(__name__)

DEFAULT_MASTER_WORKFLOW_ID = "019fd5dd-4f56-7000-8641-9bfdd6c1e3e1"
WORKFLOW_URL = "https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream"


def _get_knowledge_base_text() -> str:
    """Fetch the current knowledge base text (active policies + reference docs) so every
    Auto trigger is grounded in whatever a business user most recently edited."""
    try:
        with SessionLocal() as db:
            return build_knowledge_base_text(db)
    except Exception as e:
        log.error(f"Failed to build knowledge base text for Auto trigger: {e}")
        return "(Knowledge base unavailable.)"


def _extract_output(payload: Dict[str, Any], key: str) -> Any:
    """Search a Supervity workflow result/activity payload for an output variable."""
    if not isinstance(payload, dict):
        return None

    candidates = [
        payload.get("workflowRun", {}).get("outputs", {}).get(key),
        payload.get("workflowRun", {}).get("output", {}).get(key),
        payload.get("outputs", {}).get(key),
        payload.get("output", {}).get(key),
        payload.get(key),
    ]

    # outputs may be an array of {name, value} objects
    for outputs in [
        payload.get("workflowRun", {}).get("outputs"),
        payload.get("outputs"),
        payload.get("workflowRun", {}).get("activityRuns"),
        payload.get("activityRuns"),
    ]:
        if isinstance(outputs, list):
            for o in outputs:
                if isinstance(o, dict) and (o.get("name") == key or o.get("id") == key):
                    return o.get("value")
                # nested outputs dict
                if isinstance(o, dict):
                    for field in ("outputs", "output"):
                        nested = o.get(field)
                        if isinstance(nested, dict) and key in nested:
                            return nested[key]
                        if isinstance(nested, list):
                            for no in nested:
                                if isinstance(no, dict) and (no.get("name") == key or no.get("id") == key):
                                    return no.get("value")

    # activity-run / activityRun event content
    for prefix in ("content", "activityRun", "activity-run"):
        obj = payload.get(prefix) if isinstance(payload, dict) else None
        if isinstance(obj, dict):
            for field in ("outputs", "output"):
                nested = obj.get(field)
                if isinstance(nested, dict) and key in nested:
                    return nested[key]
                if isinstance(nested, list):
                    for no in nested:
                        if isinstance(no, dict) and (no.get("name") == key or no.get("id") == key):
                            return no.get("value")

    for c in candidates:
        if c is not None:
            return c

    return None


def _split_email_draft(text: str, original_subject: str) -> Tuple[str, str]:
    """Try to split a workflow email output into subject and body."""
    if not text:
        return original_subject, text or ""

    if isinstance(text, (dict, list)):
        if isinstance(text, dict):
            if "subject" in text and "body" in text:
                return str(text["subject"]), str(text["body"])
            if "generated_email_draft" in text:
                text = text["generated_email_draft"]

    text = str(text).strip()

    # Try to parse JSON if the whole thing looks like JSON
    if text.startswith(("{", "[")):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                if "subject" in parsed and "body" in parsed:
                    return str(parsed["subject"]), str(parsed["body"])
                if "generated_email_draft" in parsed:
                    text = str(parsed["generated_email_draft"])
        except (json.JSONDecodeError, ValueError):
            pass

    subject = original_subject
    body = text

    subject_match = re.search(r"^[\s]*(?:Subject:|Subj:?|title:?)[\s]*(.*)$", text, re.MULTILINE | re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1).strip()
        body = text[subject_match.end():].strip()

    if body.startswith("\n"):
        body = body.lstrip("\n")

    return subject, body


def _extract_email_draft(payload: Dict[str, Any], original_subject: str) -> Optional[Dict[str, str]]:
    """Extract a polished email draft from a workflow result payload."""
    if not isinstance(payload, dict):
        return None

    # Try common variable names that a workflow might expose
    for key in ["generated_email_draft", "email_draft", "email", "draft", "result"]:
        value = _extract_output(payload, key)
        if value is None:
            continue
        if isinstance(value, dict) and "subject" in value and "body" in value:
            return {"subject": str(value["subject"]), "body": str(value["body"])}
        subject, body = _split_email_draft(value, original_subject)
        if body:
            return {"subject": subject, "body": body}

    # Some workflows output top-level {subject, body}
    if "subject" in payload and "body" in payload:
        return {"subject": str(payload["subject"]), "body": str(payload["body"])}

    return None


def _parse_sse_stream(response, max_seconds: Optional[int] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse a Supervity SSE stream and return the final result payload or error.

    If max_seconds is provided, stop reading and return a timeout if the stream runs longer.
    """
    events = []
    current_event: Optional[str] = None
    current_data: List[str] = []
    start = time.monotonic()

    for raw in response.iter_lines(decode_unicode=True):
        if max_seconds is not None and (time.monotonic() - start) > max_seconds:
            raise RuntimeError("timeout")
        line = (raw or "").strip()
        if not line:
            if current_event and current_data:
                data_str = "".join(current_data)
                try:
                    payload = json.loads(data_str) if data_str else {}
                except (json.JSONDecodeError, ValueError):
                    payload = {"raw": data_str}
                events.append((current_event, payload))
                current_event = None
                current_data = []
            continue

        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data.append(line[len("data:"):].strip())

    # Handle any trailing event without a blank line
    if current_event and current_data:
        data_str = "".join(current_data)
        try:
            payload = json.loads(data_str) if data_str else {}
        except (json.JSONDecodeError, ValueError):
            payload = {"raw": data_str}
        events.append((current_event, payload))

    final_result: Optional[Dict[str, Any]] = None
    latest_activity_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    for name, payload in events:
        if name == "result":
            final_result = payload
        elif name == "error":
            error = payload.get("error") or payload.get("content") or str(payload)
        elif name in ("activity-run", "activityRun"):
            # If a Python Script step published the email, it may appear here first
            if isinstance(payload, dict):
                content = payload.get("content", payload)
                if isinstance(content, dict):
                    email = _extract_email_draft(content, "Following up")
                    if email:
                        latest_activity_output = email

    if error:
        raise RuntimeError(error)

    if final_result is not None:
        return final_result, None

    if latest_activity_output is not None:
        return {"__email_draft__": latest_activity_output}, None

    return None, None


class MasterOrchestrator:
    """
    Coordinates the entire workflow by triggering the Supervity Auto Orchestrator workflow.
    """

    @staticmethod
    def process_lead(payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        log.info(f"--- Master Orchestrator triggering Supervity Auto for {payload.get('prospect_id')} ---")

        api_key = os.getenv("WORKFLOW_API_KEY")
        workflow_id = os.getenv("SUPERVITY_WORKFLOW_ID") or DEFAULT_MASTER_WORKFLOW_ID

        # If the env variable is set to something that is not a UUID (e.g. the API key was
        # accidentally used), fall back to the default master workflow ID.
        import re
        if not re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$", workflow_id):
            log.warning(f"SUPERVITY_WORKFLOW_ID '{workflow_id[:20]}...' is not a valid UUID; using default {DEFAULT_MASTER_WORKFLOW_ID}")
            workflow_id = DEFAULT_MASTER_WORKFLOW_ID

        if not api_key:
            log.error("WORKFLOW_API_KEY is not set. Cannot trigger Auto.")
            return {"error": "WORKFLOW_API_KEY missing"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "x-source": "external",
            "x-active-org": "R.E.P.O",
            "x-user-timezone": "Asia/Kuala_Lumpur"
        }

        payload_str = json.dumps(payload)
        knowledge_base_text = _get_knowledge_base_text()

        # The Supervity Auto endpoint expects plain multipart form fields
        # (matching the existing bundler integration) rather than typed file parts.
        files = {
            "workflowId": (None, workflow_id),
            "inputs[lead_payload]": (None, payload_str),
            "inputs[knowledge_base]": (None, knowledge_base_text),
        }

        try:
            # Use the caller's timeout as both per-read and overall deadline so the
            # stream doesn't hang, but the workflow has a short window to respond.
            response = requests.post(
                WORKFLOW_URL,
                headers=headers,
                files=files,
                stream=True,
                timeout=(10, timeout),
            )
            response.raise_for_status()

            log.info("--- Supervity Auto triggered successfully ---")

            final_payload, err = _parse_sse_stream(response, max_seconds=timeout)
            if err:
                raise RuntimeError(err)
            if not final_payload:
                raise RuntimeError("Workflow completed without a result")

            # Try to extract a final email draft; if not present, return the raw workflow payload
            original_subject = payload.get("lead_stage") or "Following up"
            if "__email_draft__" in final_payload:
                return final_payload["__email_draft__"]

            email = _extract_email_draft(final_payload, original_subject)
            if email:
                return email

            return {"_raw_workflow_result": final_payload}

        except requests.exceptions.Timeout:
            log.error("Master Orchestrator timed out.")
            return {"error": "timeout"}
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to trigger Supervity Auto workflow: {e}")
            if hasattr(e, "response") and e.response is not None:
                log.error(f"Response: {e.response.text[:500]}")
            return {"error": str(e)}
        except Exception as e:
            log.error(f"Master Orchestrator processing error: {e}")
            return {"error": str(e)}


def run_operator_pipeline_batch(batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Wrapper for batch processing using the new MasterOrchestrator hitting the Auto platform."""
    results = []
    for payload in batch_data:
        res = MasterOrchestrator.process_lead(payload)
        results.append(res)
    return results
