# app/services/knowledge_base_ingest.py
"""
Knowledge Base ingestion — uses an LLM to read the project's own documentation and
data-schema/config files and turn them into Knowledge Base reference documents.

This is the "point it at your docs and SQL/config files" path: instead of a human
hand-authoring reference material, Gemini reads docs/*.md (the operational ones —
architecture, data schema, operator specs — not hackathon logistics) plus the small
config CSVs that ARE the business rules (ICP scoring weights, routing rules, sequence
definitions, territories) and distills them into titled, categorized reference docs.

Re-running ingestion replaces only the documents it previously created (source=
"ai_ingested"); anything a human wrote by hand (source="manual") or the original
seed set (source="seed") is left untouched.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import Session

from ..models.knowledge_base import KnowledgeDocument
from .llm_service import llm

log = logging.getLogger(__name__)

# Repo root as mounted into the backend container (see docker-compose.yml).
REPO_ROOT = Path(os.getenv("REPO_ROOT", "/app"))

# Curated list — operational/business-logic sources only. Hackathon logistics docs
# (brief, judging rubric, pitch outline, todo, etc.) are intentionally excluded:
# they're not knowledge the agent should reason with at runtime.
MARKDOWN_SOURCES = [
    "docs/DATA_SCHEMA.md",
    "docs/operators.md",
    "docs/sequence-operator-requirements.md",
    "docs/command-center-guide.md",
    "docs/functions.md",
]

CONFIG_SOURCES = [
    "data/ICP_Scoring_Config.csv",
    "data/Routing_Rules.csv",
    "data/Sequences.csv",
    "data/Territories.csv",
    "data/Field_Dictionary.csv",
]

MAX_CHARS_PER_FILE = 20_000  # guard against accidentally pointing this at a huge file

INGEST_PROMPT = """You are building the Knowledge Base for an AI sales-operations employee \
(the "Inbound Revenue Command Center"). Below are excerpts from this project's own \
documentation and data-configuration files.

Read them and produce a JSON array of reference documents that the AI agent should be \
given on every run so it acts correctly. Each element must be:
{{"title": string, "category": "reference"|"operator_instruction", "content": string}}

Rules:
- Extract OPERATIONAL knowledge only: data schema/field meanings, scoring formulas, \
consent/compliance rules, routing/capacity logic, sequence eligibility, edge cases and \
traps the agent must handle, operator responsibilities. Do NOT include hackathon \
logistics, judging criteria, timelines, or anything about the competition itself.
- Each document's "content" should be self-contained plain text (no markdown headers, \
no code fences) that reads like an instruction to the agent, not a description of the \
project. Be specific and keep numeric thresholds/values exact.
- Merge redundant material from different files into one clean document per topic \
rather than one document per source file.
- Produce between 4 and 10 documents.
- Respond with ONLY the JSON array, nothing else.

--- SOURCE MATERIAL ---
{sources}
"""


def _read_sources() -> Dict[str, str]:
    """Read the curated markdown + config files, truncating anything oversized."""
    contents: Dict[str, str] = {}
    for rel_path in MARKDOWN_SOURCES + CONFIG_SOURCES:
        path = REPO_ROOT / rel_path
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if len(text) > MAX_CHARS_PER_FILE:
                text = text[:MAX_CHARS_PER_FILE] + "\n...(truncated)"
            contents[rel_path] = text
        except FileNotFoundError:
            log.warning(f"Knowledge base ingest: source file not found: {path}")
        except Exception as e:
            log.error(f"Knowledge base ingest: failed to read {path}: {e}")
    return contents


def ingest_from_repo_docs(db: Session) -> Dict:
    """
    Read the curated docs/config files, ask Gemini to distill them into Knowledge
    Base documents, and replace any previously AI-ingested documents with the result.
    """
    sources = _read_sources()
    if not sources:
        return {"status": "error", "message": "No source files could be read.", "documents": []}

    sources_blob = "\n\n".join(
        f"=== {path} ===\n{text}" for path, text in sources.items()
    )
    prompt = INGEST_PROMPT.format(sources=sources_blob)

    try:
        result = llm.gemini_json(prompt)
    except RuntimeError as e:
        # Gemini not configured
        return {"status": "error", "message": str(e), "documents": []}
    except Exception as e:
        log.error(f"Knowledge base ingestion failed: {e}")
        return {"status": "error", "message": f"AI ingestion failed: {e}", "documents": []}

    if not isinstance(result, list):
        return {"status": "error", "message": "The model did not return a JSON array.", "documents": []}

    # Replace the previous AI-ingested batch (leave manual/seed docs untouched).
    db.query(KnowledgeDocument).filter(KnowledgeDocument.source == "ai_ingested").delete()

    created: List[KnowledgeDocument] = []
    for item in result:
        if not isinstance(item, dict) or not item.get("title") or not item.get("content"):
            continue
        doc = KnowledgeDocument(
            title=str(item["title"])[:255],
            category=str(item.get("category") or "reference"),
            content=str(item["content"]),
            is_active=True,
            source="ai_ingested",
        )
        db.add(doc)
        created.append(doc)

    db.commit()
    for doc in created:
        db.refresh(doc)

    log.info(f"Knowledge base ingestion created {len(created)} documents from {len(sources)} source files.")

    return {
        "status": "success",
        "sources_read": list(sources.keys()),
        "documents": [{"id": d.id, "title": d.title, "category": d.category} for d in created],
    }
