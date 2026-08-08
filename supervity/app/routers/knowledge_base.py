# app/routers/knowledge_base.py
"""Knowledge Base — reference documents CRUD + the assembled text sent to Auto."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.knowledge_base import KnowledgeDocument as KnowledgeDocumentModel
from ..schemas.knowledge_base import (
    KnowledgeBaseText,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
)
from ..services import knowledge_base as kb_service
from ..services.knowledge_base_ingest import ingest_from_repo_docs
from ..services.audit import audit, AuditCategory, AuditSeverity

log = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


# =========================================================================
# ASSEMBLED TEXT — what gets sent to Auto on every run
# =========================================================================

@router.get("", response_model=KnowledgeBaseText)
def get_knowledge_base(db: Session = Depends(get_db)):
    """Return the current assembled knowledge base (active policies + active reference docs)."""
    return kb_service.build_knowledge_base(db)


# =========================================================================
# AI INGESTION — Gemini reads docs/*.md + data config files -> reference docs
# =========================================================================

@router.post("/ingest")
def ingest_knowledge_base(db: Session = Depends(get_db)):
    """
    Use Gemini to read this project's own docs/*.md and data config/schema files and
    turn them into Knowledge Base reference documents. Replaces the previous AI-ingested
    batch; manual and seed documents are untouched.
    """
    result = ingest_from_repo_docs(db)

    if result["status"] == "success":
        audit.log_sync(
            action="knowledge_base.ai_ingest",
            description=f"AI ingested {len(result['documents'])} knowledge base documents from repo docs/config files.",
            category=AuditCategory.SETTINGS,
            severity=AuditSeverity.INFO,
            resource_type="kb_document",
            metadata={"sources_read": result.get("sources_read", []), "documents": result["documents"]},
            actor={"id": "dev-user", "email": "dev-user@supervity.ai"},
        )
        return result

    raise HTTPException(status_code=503, detail=result["message"])


# =========================================================================
# REFERENCE DOCUMENT CRUD
# =========================================================================

@router.get("/documents", response_model=list[KnowledgeDocument])
def list_documents(db: Session = Depends(get_db)):
    return (
        db.query(KnowledgeDocumentModel)
        .order_by(KnowledgeDocumentModel.category.asc(), KnowledgeDocumentModel.title.asc())
        .all()
    )


@router.post("/documents", response_model=KnowledgeDocument)
def create_document(doc: KnowledgeDocumentCreate, db: Session = Depends(get_db)):
    db_doc = KnowledgeDocumentModel(**doc.model_dump(), source="manual")
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    audit.log_sync(
        action="knowledge_base.document_created",
        description=f"Created knowledge base document '{db_doc.title}'.",
        category=AuditCategory.SETTINGS,
        severity=AuditSeverity.INFO,
        resource_type="kb_document",
        resource_id=db_doc.id,
        resource_name=db_doc.title,
        actor={"id": "dev-user", "email": "dev-user@supervity.ai"},
    )
    return db_doc


@router.get("/documents/{document_id}", response_model=KnowledgeDocument)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/documents/{document_id}", response_model=KnowledgeDocument)
@router.patch("/documents/{document_id}", response_model=KnowledgeDocument)
def update_document(document_id: int, updates: KnowledgeDocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)

    audit.log_sync(
        action="knowledge_base.document_updated",
        description=f"Updated knowledge base document '{doc.title}'. Agents will use the new text on their next run.",
        category=AuditCategory.SETTINGS,
        severity=AuditSeverity.INFO,
        resource_type="kb_document",
        resource_id=doc.id,
        resource_name=doc.title,
        actor={"id": "dev-user", "email": "dev-user@supervity.ai"},
    )
    return doc


@router.patch("/documents/{document_id}/toggle", response_model=KnowledgeDocument)
def toggle_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.is_active = not doc.is_active
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    title = doc.title
    db.delete(doc)
    db.commit()

    audit.log_sync(
        action="knowledge_base.document_deleted",
        description=f"Deleted knowledge base document '{title}'.",
        category=AuditCategory.SETTINGS,
        severity=AuditSeverity.WARNING,
        resource_type="kb_document",
        resource_id=document_id,
        resource_name=title,
        actor={"id": "dev-user", "email": "dev-user@supervity.ai"},
    )
    return {"message": "Document deleted", "id": document_id}
