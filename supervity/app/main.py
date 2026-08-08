# app/main.py
"""
FastAPI Application Entry Point

This is the main application file that:
- Creates the FastAPI app instance
- Configures CORS middleware
- Configures Audit middleware (automatic request/response logging)
- Registers all API routers
- Sets up the authorization middleware
- Exposes PostgreSQL Data Pack endpoints
"""

import io
import logging
import os

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import create_engine, text

from .authz import AuthzEngine
from .core.database import Base
from .core.storage import GCSStorage, LocalStorage, StorageBackend
from .middleware import AuditMiddleware
from .routers import (
    admin_router,
    audit_router,
    auth_router,
    dashboard_router,
    data_manager_router,
    examples_router,
    exceptions_router,
    health_router,
    insights_router,
    items_router,
    llm_router,
    bundler_router,
    policies_router,
    ai_policies_router,
    ai_chat_router,
    permissions_router,
    settings_router,
    operators_router,
    contacts_router,
    workbench_router,
    knowledge_base_router,
    org_router,
)
from .security import get_current_user, verify_access

log = logging.getLogger(__name__)

# =============================================================================
# BASE PATH CONFIGURATION
# =============================================================================

BASE_PATH = os.getenv("BASE_PATH", "")
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = f"/{BASE_PATH}"
if BASE_PATH == "/":
    BASE_PATH = ""

log.info(f"API Base Path: '{BASE_PATH}' (empty means root)")

# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="AutoPilot API",
    description="AI Command Center — Full-stack template with FastAPI, Next.js, and PostgreSQL",
    version="2.0.0",
    docs_url=f"{BASE_PATH}/api/docs",
    redoc_url=f"{BASE_PATH}/api/redoc",
    openapi_url=f"{BASE_PATH}/api/openapi.json",
)

@app.on_event("startup")
def on_startup():
    from .core.database import engine
    # Create all tables (does not overwrite existing ones)
    Base.metadata.create_all(bind=engine)
    log.info("Database tables verified/created.")

    # create_all() does not add new columns to pre-existing tables — patch those in.
    from .core.schema_patch import apply_additive_columns
    apply_additive_columns(engine)

    from .core.database import SessionLocal
    from .services.knowledge_base_seed import seed_default_documents
    from .services.org_seed import seed_org_hierarchy
    with SessionLocal() as db:
        seed_default_documents(db)
        seed_org_hierarchy(db)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3001")
cors_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

# =============================================================================
# API ROUTER WITH AUTHORIZATION
# =============================================================================

api_router = APIRouter(
    prefix=f"{BASE_PATH}/api",
    dependencies=[Depends(verify_access)],
)

# =============================================================================
# STORAGE DEPENDENCY
# =============================================================================


def get_storage_dependency() -> StorageBackend:
    """Get the appropriate storage backend based on environment."""
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "gcs":
        bucket = os.getenv("GCS_BUCKET")
        prefix = os.getenv("GCS_PREFIX", "")
        if not bucket:
            raise ValueError("GCS_BUCKET environment variable is required")
        return GCSStorage(bucket, prefix)
    else:
        path = os.getenv("LOCAL_STORAGE_PATH", "./document_storage")
        return LocalStorage(path)


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(audit_router)
api_router.include_router(items_router)
api_router.include_router(examples_router)
api_router.include_router(llm_router)
api_router.include_router(dashboard_router)
api_router.include_router(policies_router)
api_router.include_router(exceptions_router)
api_router.include_router(insights_router)
api_router.include_router(data_manager_router)
api_router.include_router(bundler_router)
api_router.include_router(ai_policies_router)
api_router.include_router(ai_chat_router)
api_router.include_router(permissions_router)
api_router.include_router(settings_router)
api_router.include_router(operators_router)
api_router.include_router(contacts_router)
api_router.include_router(workbench_router)
api_router.include_router(knowledge_base_router)
api_router.include_router(org_router)


# =============================================================================
# DATA PACK ENDPOINTS (POSTGRESQL READS)
# =============================================================================

# Targets the internal Docker network host 'postgres'
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/app_db")
db_engine = create_engine(DB_URL)

ALLOWED_TABLES = {
    "account", "buying_group", "consent_register", "contact",
    "enrichment_data", "field_dictionary", "icp_scoring_config",
    "opportunity", "routing_rules", "sdr_roster", "sequences",
    "territories", "visitoractivity"
}


@api_router.get("/data/{table_name}", tags=["Data Pack"])
async def get_table_data(table_name: str, limit: int = 100):
    """Fetch records from any seeded PostgreSQL database table."""
    clean_table = table_name.lower().strip()
    
    if clean_table not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Table '{table_name}' not found. Allowed tables: {', '.join(sorted(ALLOWED_TABLES))}"
        )

    try:
        with db_engine.connect() as conn:
            query = text(f"SELECT * FROM {clean_table} LIMIT :limit")
            result = conn.execute(query, {"limit": limit})
            records = [dict(row._mapping) for row in result]

        return {
            "status": "success",
            "table": clean_table,
            "count": len(records),
            "data": records
        }
    except Exception as e:
        log.error(f"Error reading from table {clean_table}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FILE STORAGE ENDPOINTS
# =============================================================================


@api_router.get("/files/", tags=["Files"])
async def list_files(
    prefix: str = "",
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    """List all files in storage, optionally filtered by prefix."""
    files = await storage.list_files(prefix)
    return {"files": files, "count": len(files)}


@api_router.post("/files/{file_path:path}", tags=["Files"])
async def upload_file(
    file_path: str,
    file: UploadFile = File(...),
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    """Upload a file to storage."""
    content = await file.read()
    url = await storage.save(file_path, content, file.content_type)
    return {
        "path": file_path,
        "url": url,
        "content_type": file.content_type,
        "size": len(content),
    }


@api_router.get("/files/{file_path:path}", tags=["Files"])
async def download_file(
    file_path: str,
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    """Download a file from storage."""
    try:
        content, content_type = await storage.load(file_path)
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file_path}"'},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@api_router.delete("/files/{file_path:path}", tags=["Files"])
async def delete_file(
    file_path: str,
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    """Delete a file from storage."""
    await storage.delete(file_path)
    return {"status": "deleted", "path": file_path}


# =============================================================================
# MOUNT ROUTERS TO APP
# =============================================================================

app.include_router(api_router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "AutoPilot API",
        "version": "2.0.0",
        "docs": f"{BASE_PATH}/api/docs",
        "health": f"{BASE_PATH}/api/health",
        "base_path": BASE_PATH or "/",
    }


if BASE_PATH:

    @app.get(BASE_PATH)
    async def base_path_root():
        """Base path root endpoint - API information."""
        return {
            "name": "AutoPilot API",
            "version": "2.0.0",
            "docs": f"{BASE_PATH}/api/docs",
            "health": f"{BASE_PATH}/api/health",
            "base_path": BASE_PATH,
        }