# app/routers/__init__.py
"""
API Routers - Modular endpoint organization.

Note: File endpoints are defined in main.py to maintain proper path ordering.
"""

from .admin import router as admin_router
from .audit import router as audit_router
from .auth import router as auth_router
from .bundler import router as bundler_router
from .contacts import router as contacts_router
from .dashboard import router as dashboard_router
from .data_manager import router as data_manager_router
from .examples import router as examples_router
from .exceptions import router as exceptions_router
from .health import router as health_router
from .insights import router as insights_router
from .items import router as items_router
from .llm import router as llm_router
from .policies import router as policies_router
from .permissions import router as permissions_router, settings_router as settings_router
from .ai_policies import router as ai_policies_router
from .ai_chat import router as ai_chat_router
from .operators import router as operators_router
from .workbench import router as workbench_router
from .knowledge_base import router as knowledge_base_router
from .org import router as org_router

__all__ = [
    "admin_router",
    "audit_router",
    "auth_router",
    "bundler_router",
    "contacts_router",
    "dashboard_router",
    "data_manager_router",
    "examples_router",
    "exceptions_router",
    "health_router",
    "insights_router",
    "items_router",
    "llm_router",
    "policies_router",
    "ai_policies_router",
    "ai_chat_router",
    "permissions_router",
    "settings_router",
    "operators_router",
    "workbench_router",
    "knowledge_base_router",
    "org_router",
]
