# app/services/policy_engine.py
"""
AI Policy Engine — Runtime evaluation of structured and natural language policies.

This service:
1. Evaluates structured (IF/THEN DSL) policies deterministically
2. Evaluates natural language policies via Gemini LLM
3. Translates natural language rules into structured DSL via LLM
4. Detects conflicts between policies
5. Analyzes proposed rules for clarity and completeness
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.policy import Policy as PolicyModel
from ..services.audit import audit, AuditCategory, AuditSeverity
from .llm_service import llm

log = logging.getLogger(__name__)

# =========================================================================
# POLICY SYSTEM PROMPTS
# =========================================================================

TRANSLATE_PROMPT = """You are an enterprise AI policy engine for a Sales Intelligence system.
Given a natural language business rule, translate it into a structured DSL (Domain-Specific Language) format.

Output a JSON object with these fields:
- "dsl": an object with:
    - "conditions": array of {"field": string, "operator": string, "value": string}
      Valid operators: "equals", "not_equals", "greater_than", "less_than", "contains", "in", "not_in"
    - "actions": array of {"type": string, "value": string}
      Valid action types: "approve", "reject", "escalate", "flag", "notify", "require_review", "block"
    - "match_mode": "all" or "any"
- "confidence": a number 0.0-1.0 indicating how confident you are in the translation

Respond ONLY with valid JSON."""

ANALYZE_PROMPT = """You are an enterprise AI policy engine for a Sales Intelligence system.
Analyze the following business rule and provide:
- "refined_instruction": a clearer, more precise version of the rule
- "entity_name": what entity this rule applies to (e.g., "lead", "contact", "opportunity", "deal")
- "impact_assessment": brief description of what this policy will affect
- "suggested_conditions": array of conditions that could be extracted
- "suggested_actions": array of actions that should be taken
- "edge_cases": array of potential edge cases or ambiguities
- "confidence": 0.0-1.0

Respond ONLY with valid JSON."""

CONFLICT_CHECK_PROMPT = """You are an enterprise AI policy engine. Given an existing set of policies and a new proposed policy, check for:
1. Direct conflicts (policies that contradict each other)
2. Overrides (new policy would override existing ones)
3. Ambiguities that need clarification

Existing policies:
{existing_policies}

New proposed policy:
{new_policy}

Return a JSON object:
- "conflicts": array of {{"id": string, "description": string, "severity": "high"|"medium"|"low"}}
- "overrides": array of {{"id": string, "description": string}}
- "clarifications": array of string
- "suggested_instructions": array of string
- "refined_instruction": improved version of the new policy
- "is_valid": boolean
- "warnings": array of string

Respond ONLY with valid JSON."""

EVALUATE_PROMPT = """You are an AI policy enforcer for a Sales Intelligence system.
Given the following business policy and the data context, determine if the policy applies and what action should be taken.

Policy: {policy_instruction}

Data Context:
{data_context}

Return a JSON object:
- "applies": boolean (does this policy apply to this data?)
- "action": string (what action to take: "approve", "reject", "escalate", "flag", "no_action")
- "reason": string (brief explanation)
- "confidence": 0.0-1.0

Respond ONLY with valid JSON."""


# =========================================================================
# STRUCTURED DSL EVALUATOR
# =========================================================================

def evaluate_dsl_condition(condition: Dict, data: Dict) -> bool:
    """Evaluate a single structured condition against data."""
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    target_value = condition.get("value", "")
    
    actual_value = data.get(field)
    if actual_value is None:
        return False
    
    actual_str = str(actual_value).strip().lower()
    target_str = str(target_value).strip().lower()
    
    if operator == "equals":
        return actual_str == target_str
    elif operator == "not_equals":
        return actual_str != target_str
    elif operator == "greater_than":
        try:
            return float(actual_value) > float(target_value)
        except (ValueError, TypeError):
            return False
    elif operator == "less_than":
        try:
            return float(actual_value) < float(target_value)
        except (ValueError, TypeError):
            return False
    elif operator == "contains":
        return target_str in actual_str
    elif operator == "in":
        # target_value should be a comma-separated list
        allowed = [v.strip().lower() for v in str(target_value).split(",")]
        return actual_str in allowed
    elif operator == "not_in":
        blocked = [v.strip().lower() for v in str(target_value).split(",")]
        return actual_str not in blocked
    else:
        log.warning(f"Unknown operator: {operator}")
        return False


def evaluate_structured_policy(dsl: Dict, data: Dict) -> Dict:
    """Evaluate a structured (IF/THEN) policy against data."""
    conditions = dsl.get("conditions", [])
    actions = dsl.get("actions", [])
    match_mode = dsl.get("match_mode", "all")
    
    if not conditions:
        return {"applies": False, "action": "no_action", "reason": "No conditions defined"}
    
    results = [evaluate_dsl_condition(c, data) for c in conditions]
    
    if match_mode == "all":
        matches = all(results)
    else:
        matches = any(results)
    
    if matches and actions:
        primary_action = actions[0]
        return {
            "applies": True,
            "action": primary_action.get("type", "flag"),
            "reason": f"Policy matched ({match_mode} conditions met)",
            "confidence": 1.0,
            "matched_conditions": [c for c, r in zip(conditions, results) if r],
        }
    
    return {"applies": False, "action": "no_action", "reason": "Conditions not met", "confidence": 1.0}


# =========================================================================
# LLM-POWERED POLICY FUNCTIONS
# =========================================================================

def translate_to_dsl(natural_language: str) -> Dict:
    """Translate natural language rule into structured DSL using LLM."""
    try:
        result = llm.gemini_json(
            TRANSLATE_PROMPT + f"\n\nBusiness Rule: \"{natural_language}\""
        )
        if isinstance(result, dict):
            return result
        return {"dsl": None, "confidence": 0.0}
    except Exception as e:
        log.error(f"DSL translation failed: {e}")
        return {"dsl": None, "confidence": 0.0, "error": str(e)}


def analyze_rule(natural_language: str, policy_type: str = None, entity_name: str = None) -> Dict:
    """Analyze a proposed rule for clarity, completeness, and edge cases."""
    extra_context = ""
    if policy_type:
        extra_context += f"\nPolicy Type: {policy_type}"
    if entity_name:
        extra_context += f"\nEntity: {entity_name}"
    
    try:
        result = llm.gemini_json(
            ANALYZE_PROMPT + f"\n\nBusiness Rule: \"{natural_language}\"{extra_context}"
        )
        if isinstance(result, dict):
            return result
        return {"refined_instruction": natural_language, "confidence": 0.5}
    except Exception as e:
        log.error(f"Rule analysis failed: {e}")
        return {
            "refined_instruction": natural_language,
            "confidence": 0.0,
            "error": str(e),
        }


def check_conflicts(natural_language: str, policy_scope: str, entity_name: str, db: Session) -> Dict:
    """Check if a new policy conflicts with existing active policies."""
    # Fetch all active policies
    existing = db.query(PolicyModel).filter(PolicyModel.is_active == True).all()
    
    if not existing:
        return {
            "conflicts": [],
            "overrides": [],
            "clarifications": [],
            "suggested_instructions": [],
            "refined_instruction": natural_language,
            "is_valid": True,
            "warnings": [],
        }
    
    existing_summary = "\n".join(
        [f"- Policy #{p.id} ({p.name}): {p.natural_language}" for p in existing]
    )
    
    prompt = CONFLICT_CHECK_PROMPT.format(
        existing_policies=existing_summary,
        new_policy=natural_language,
    )
    
    try:
        result = llm.gemini_json(prompt)
        if isinstance(result, dict):
            return result
    except Exception as e:
        log.error(f"Conflict check failed: {e}")
    
    return {
        "conflicts": [],
        "overrides": [],
        "clarifications": [],
        "suggested_instructions": [],
        "refined_instruction": natural_language,
        "is_valid": True,
        "warnings": ["Conflict check could not be completed"],
    }


def evaluate_policy(policy: PolicyModel, data: Dict) -> Dict:
    """
    Evaluate a single policy against data.
    Uses structured DSL for logical policies, LLM for natural language policies.
    """
    if policy.policy_type == "logical" and policy.dsl:
        result = evaluate_structured_policy(policy.dsl, data)
        result["policy_id"] = policy.id
        result["policy_name"] = policy.name
        
        if result.get("applies"):
            log.info(f"Structured Policy '{policy.name}' matched payload.")
            audit.log_sync(
                action="policy.triggered",
                description=f"Structured Policy '{policy.name}' matched payload.",
                category=AuditCategory.SYSTEM,
                severity=AuditSeverity.WARNING,
                resource_type="policy",
                resource_id=policy.id,
                resource_name=policy.name,
                metadata={"payload": data},
                actor={"id": "system", "email": "policy_engine@supervity.ai"}
            )
        return result
    
    # Natural language evaluation via LLM
    instruction = policy.refined_instruction or policy.ai_instruction or policy.natural_language
    
    prompt = EVALUATE_PROMPT.format(
        policy_instruction=instruction,
        data_context=json.dumps(data, indent=2, default=str),
    )
    
    try:
        result = llm.gemini_json(prompt)
        if isinstance(result, dict):
            result["policy_id"] = policy.id
            result["policy_name"] = policy.name
            
            if result.get("applies"):
                log.info(f"NL Policy '{policy.name}' matched payload. Reason: {result.get('reason')}")
                audit.log_sync(
                    action="policy.triggered",
                    description=f"NL Policy '{policy.name}' matched payload. Reason: {result.get('reason')}",
                    category=AuditCategory.SYSTEM,
                    severity=AuditSeverity.WARNING,
                    resource_type="policy",
                    resource_id=policy.id,
                    resource_name=policy.name,
                    metadata={"payload": data, "reason": result.get("reason")},
                    actor={"id": "system", "email": "policy_engine@supervity.ai"}
                )
            return result
    except Exception as e:
        log.error(f"Policy evaluation failed for policy {policy.id}: {e}")
    
    return {
        "policy_id": policy.id,
        "policy_name": policy.name,
        "applies": False,
        "action": "no_action",
        "reason": "Evaluation failed",
        "confidence": 0.0,
    }


def evaluate_all_policies(data: Dict, db: Session, entity_name: str = None) -> List[Dict]:
    """Evaluate ALL active policies against a data payload."""
    query = db.query(PolicyModel).filter(PolicyModel.is_active == True)
    if entity_name:
        query = query.filter(PolicyModel.entity_name == entity_name)
    
    policies = query.order_by(PolicyModel.priority.asc()).all()
    
    results = []
    for policy in policies:
        result = evaluate_policy(policy, data)
        results.append(result)
        
        # Update execution stats
        from datetime import datetime
        policy.execution_count = (policy.execution_count or 0) + 1
        policy.last_executed_at = datetime.utcnow()
    
    db.commit()
    return results
