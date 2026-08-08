# app/services/knowledge_base.py
"""
Knowledge Base assembly — turns active AI Policies + reference documents into a single
text corpus that is handed to the Auto Orchestrator/Operators on every run.

This is what makes "editing a policy changes agent behavior on the next run" true end
to end: the moment a policy or reference doc is saved (text, no code) it is picked up
here, and every subsequent call to `build_knowledge_base_text()` — including the one
the bundler/operators make right before triggering Auto — reflects the edit.
"""

from datetime import datetime, timezone
from typing import Dict

from sqlalchemy.orm import Session

from ..models.knowledge_base import KnowledgeDocument
from ..models.policy import Policy as PolicyModel

KB_HEADER = (
    "# SUPERVITY KNOWLEDGE BASE\n"
    "This is the live, business-editable knowledge base for the Inbound Revenue AI Employee.\n"
    "It is regenerated on every run — always follow the CURRENT text below, not any\n"
    "version of these rules you may have seen in a previous run.\n"
)


def _render_policy(p: PolicyModel) -> str:
    lines = [f"### Policy #{p.id} — {p.name} (priority {p.priority})"]
    if p.description:
        lines.append(p.description)
    if p.policy_type == "logical" and p.dsl:
        conditions = p.dsl.get("conditions", []) if isinstance(p.dsl, dict) else []
        actions = p.dsl.get("actions", []) if isinstance(p.dsl, dict) else []
        match_mode = p.dsl.get("match_mode", "all") if isinstance(p.dsl, dict) else "all"
        cond_text = f" {match_mode.upper()} ".join(
            f"{c.get('field')} {c.get('operator')} {c.get('value')}" for c in conditions
        )
        action_text = ", ".join(a.get("type", "") for a in actions)
        lines.append(f"IF {cond_text} THEN {action_text}.")
    instruction = p.refined_instruction or p.ai_instruction or p.natural_language
    lines.append(f"Rule: {instruction}")
    if p.entity_name:
        lines.append(f"Applies to: {p.entity_name}")
    return "\n".join(lines)


def _render_document(d: KnowledgeDocument) -> str:
    return f"### {d.title} [{d.category}]\n{d.content}"


def get_active_policy_text(db: Session) -> str:
    policies = (
        db.query(PolicyModel)
        .filter(PolicyModel.is_active == True)  # noqa: E712
        .order_by(PolicyModel.priority.asc())
        .all()
    )
    if not policies:
        return "(No active policies.)"
    return "\n\n".join(_render_policy(p) for p in policies)


def get_active_document_text(db: Session) -> str:
    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.is_active == True)  # noqa: E712
        .order_by(KnowledgeDocument.category.asc(), KnowledgeDocument.title.asc())
        .all()
    )
    if not docs:
        return "(No reference documents.)"
    return "\n\n".join(_render_document(d) for d in docs)


def build_knowledge_base(db: Session) -> Dict:
    """Assemble the full knowledge base text plus counts, ready to hand to Auto."""
    policies = (
        db.query(PolicyModel).filter(PolicyModel.is_active == True).all()  # noqa: E712
    )
    docs = (
        db.query(KnowledgeDocument).filter(KnowledgeDocument.is_active == True).all()  # noqa: E712
    )

    text = "\n\n".join(
        [
            KB_HEADER,
            "## AI POLICIES (governance — these constrain what the agent may do alone)",
            get_active_policy_text(db),
            "## REFERENCE DOCUMENTS (domain knowledge the agent should use)",
            get_active_document_text(db),
        ]
    )

    return {
        "text": text,
        "policy_count": len(policies),
        "document_count": len(docs),
        "generated_at": datetime.now(timezone.utc),
    }


def build_knowledge_base_text(db: Session) -> str:
    """Convenience wrapper returning just the text, for inlining into an Auto payload."""
    return build_knowledge_base(db)["text"]
