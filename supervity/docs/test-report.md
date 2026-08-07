# Supervity Website Test Report

Generated: 2026-08-07T20:21:37.609822Z

## Executive Summary
- Frontend build: passing
- Backend build: passing
- Frontend routes tested: 17
- Backend endpoints discovered: 142
- Functional features tested: 19
- Frontend route failures: 0
- Functional feature failures: 6

## Container Status
```
NAME                   IMAGE                COMMAND                  SERVICE    CREATED         STATUS                   PORTS
supervity-backend-1    supervity-backend    "sh start_gunicorn.sh"   backend    3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:8001->8000/tcp
supervity-frontend-1   supervity-frontend   "docker-entrypoint.sâ€¦"   frontend   3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:3001->3000/tcp
supervity-postgres-1   postgres:15-alpine   "docker-entrypoint.sâ€¦"   postgres   33 hours ago    Up 14 hours (healthy)    0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp

```

## Frontend Routes
| Route | Source | Status | Length | Error Text |
|-------|--------|--------|--------|------------|
| / | C:/supervity/supervity/frontend/src/app/page.tsx | 200 | 95070 | no |
| /admin/audit | C:/supervity/supervity/frontend/src/app/admin/audit/page.tsx | 200 | 35570 | no |
| /admin/events | C:/supervity/supervity/frontend/src/app/admin/events/page.tsx | 200 | 28859 | no |
| /admin/groups | C:/supervity/supervity/frontend/src/app/admin/groups/page.tsx | 200 | 28860 | no |
| /admin/roles | C:/supervity/supervity/frontend/src/app/admin/roles/page.tsx | 200 | 47890 | no |
| /admin/sessions | C:/supervity/supervity/frontend/src/app/admin/sessions/page.tsx | 200 | 28874 | no |
| /admin/settings | C:/supervity/supervity/frontend/src/app/admin/settings/page.tsx | 200 | 47806 | no |
| /admin/users | C:/supervity/supervity/frontend/src/app/admin/users/page.tsx | 200 | 96489 | no |
| /ai/insights | C:/supervity/supervity/frontend/src/app/ai/insights/page.tsx | 200 | 60712 | no |
| /ai/policies | C:/supervity/supervity/frontend/src/app/ai/policies/page.tsx | 200 | 38570 | no |
| /auth/error | C:/supervity/supervity/frontend/src/app/auth/error/page.tsx | 200 | 9744 | no |
| /auth/register | C:/supervity/supervity/frontend/src/app/auth/register/page.tsx | 200 | 23442 | no |
| /auth/signin | C:/supervity/supervity/frontend/src/app/auth/signin/page.tsx | 200 | 9801 | no |
| /data-manager | C:/supervity/supervity/frontend/src/app/data-manager/page.tsx | 200 | 32419 | no |
| /settings | C:/supervity/supervity/frontend/src/app/settings/page.tsx | 200 | 44898 | no |
| /workbench | C:/supervity/supervity/frontend/src/app/workbench/page.tsx | 200 | 38522 | no |
| /workbench/users | C:/supervity/supervity/frontend/src/app/workbench/users/page.tsx | 200 | 30900 | no |

## Backend API Smoke Tests
| Method | Path | Status | Summary | Response Snippet |
|--------|------|--------|---------|------------------|
| GET | / | 200 | Root | {"name": "AutoPilot API", "version": "2.0.0", "docs": "/api/docs", "health": "/a |
| GET | /api/admin/audit | 200 | List Audit Logs | {"logs": [{"id": 1273, "timestamp": "2026-08-07T20:20:09.257383Z", "actor_id": n |
| GET | /api/admin/audit/actions | 200 | List Audit Actions | {"actions": ["user.approve", "api.get", "api.delete.admin.users", "api.get.admin |
| GET | /api/admin/audit/actor/{actor_email} | 200 | Get Actor Audit Trail | {"actor_email": "{actor_email}", "logs": [], "total": 0, "page": 1, "page_size": |
| GET | /api/admin/audit/categories | 200 | List Audit Categories | {"categories": ["settings", "api", "data", "admin", "system", "user_management", |
| GET | /api/admin/audit/export | 200 | Export Audit Logs | ID,Timestamp,Actor Email,Actor IP,Action,Category,Severity,Resource Type,Resourc |
| GET | /api/admin/audit/resource/{resource_type}/{resource_id} | 200 | Get Resource Audit Trail | {"resource_type": "{resource_type}", "resource_id": "{resource_id}", "logs": [], |
| GET | /api/admin/audit/stats | 200 | Get Audit Stats | {"total_events": 1273, "events_today": 799, "events_this_week": 1273, "by_catego |
| GET | /api/admin/audit/{audit_id} | 422 | Get Audit Log | {"detail":[{"type":"int_parsing","loc":["path","audit_id"],"msg":"Input should b |
| GET | /api/admin/dashboard | 200 | Get Admin Dashboard | {"message": "Welcome to the admin dashboard, dev-user"} |
| GET | /api/admin/events | 500 | List Login Events | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| GET | /api/admin/events/admin | 500 | List Admin Events | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| GET | /api/admin/events/summary | 500 | Get Login Events Summary | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| GET | /api/admin/events/types | 501 | Get Event Types | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| GET | /api/admin/groups | 500 | List All Groups | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/groups | 422 | Create Group | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| DELETE | /api/admin/groups/{group_id} | SKIPPED | Delete Group | destructive; not tested |
| GET | /api/admin/groups/{group_id} | 501 | Get Group | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| PUT | /api/admin/groups/{group_id} | 422 | Update Group | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| GET | /api/admin/groups/{group_id}/members | 500 | Get Group Members | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/groups/{group_id}/members | 422 | Add Group Member | {"detail":[{"type":"missing","loc":["body","user_id"],"msg":"Field required","in |
| DELETE | /api/admin/groups/{group_id}/members/{member_user_id} | SKIPPED | Remove Group Member | destructive; not tested |
| POST | /api/admin/groups/{group_id}/roles | 422 | Assign Role To Group | {"detail":[{"type":"missing","loc":["body","role_name"],"msg":"Field required"," |
| DELETE | /api/admin/groups/{group_id}/roles/{role_name} | SKIPPED | Remove Role From Group | destructive; not tested |
| GET | /api/admin/roles | 500 | List All Roles | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/roles | 422 | Create Role | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| DELETE | /api/admin/roles/{role_name} | SKIPPED | Delete Role | destructive; not tested |
| GET | /api/admin/roles/{role_name} | 501 | Get Role | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| PUT | /api/admin/roles/{role_name} | 422 | Update Role | {"detail":[{"type":"missing","loc":["body","description"],"msg":"Field required" |
| GET | /api/admin/roles/{role_name}/users | 500 | Get Role Users | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| GET | /api/admin/sessions | 500 | List All Sessions | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| GET | /api/admin/sessions/stats | 500 | Get Session Stats | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| DELETE | /api/admin/sessions/{session_id} | SKIPPED | Terminate Session | destructive; not tested |
| GET | /api/admin/settings/approved-domains | 200 | Get Approved Domains | {"domains": ["example.com"], "message": "1 approved domain(s) configured."} |
| POST | /api/admin/settings/approved-domains | 422 | Update Approved Domains | {"detail":[{"type":"missing","loc":["body","domains"],"msg":"Field required","in |
| GET | /api/admin/users | 500 | List All Users | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/users | 422 | Admin Create User | {"detail":[{"type":"missing","loc":["body","email"],"msg":"Field required","inpu |
| DELETE | /api/admin/users/bulk | 422 | Bulk Delete Users By Domain | {"detail":[{"type":"missing","loc":["query","domain"],"msg":"Field required","in |
| POST | /api/admin/users/bulk/revoke | 422 | Bulk Revoke Users By Domain | {"detail":[{"type":"missing","loc":["query","domain"],"msg":"Field required","in |
| GET | /api/admin/users/pending | 500 | List Pending Users | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| DELETE | /api/admin/users/reset | 400 | Reset All Non Admin Users | {"detail":"Must pass confirm=true to execute reset"} |
| DELETE | /api/admin/users/{user_id} | SKIPPED | Delete User | destructive; not tested |
| POST | /api/admin/users/{user_id}/approve | 500 | Approve User | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/users/{user_id}/logout | 501 | Logout User | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| POST | /api/admin/users/{user_id}/make-admin | 500 | Make User Admin | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/users/{user_id}/reject | 500 | Reject User | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/users/{user_id}/remove-admin | 501 | Remove User Admin | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| POST | /api/admin/users/{user_id}/reset-password | 422 | Reset User Password | {"detail":[{"type":"missing","loc":["body","password"],"msg":"Field required","i |
| POST | /api/admin/users/{user_id}/restore | 500 | Restore User Access | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/admin/users/{user_id}/revoke | 501 | Revoke User Access | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| GET | /api/admin/users/{user_id}/roles | 501 | Get User Roles | {"detail":"User management requires Keycloak. Set AUTH_BYPASS=false and configur |
| POST | /api/admin/users/{user_id}/roles | 422 | Assign Role To User | {"detail":[{"type":"missing","loc":["body","role_name"],"msg":"Field required"," |
| DELETE | /api/admin/users/{user_id}/roles/{role_name} | SKIPPED | Remove Role From User | destructive; not tested |
| GET | /api/admin/users/{user_id}/sessions | 500 | Get User Sessions | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and con |
| POST | /api/ai/chat | 422 | Ai Chat | {"detail":[{"type":"missing","loc":["body","message"],"msg":"Field required","in |
| GET | /api/ai/policies | 200 | List Policies | [{"name": "VIP Customer Ticket Escalation", "description": "", "natural_language |
| POST | /api/ai/policies | 422 | Create Policy | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| POST | /api/ai/policies/analyze | 422 | Analyze Policy | {"detail":[{"type":"missing","loc":["body","natural_language"],"msg":"Field requ |
| POST | /api/ai/policies/translate | 422 | Translate Policy | {"detail":[{"type":"missing","loc":["body","natural_language"],"msg":"Field requ |
| DELETE | /api/ai/policies/{policy_id} | SKIPPED | Delete Policy | destructive; not tested |
| GET | /api/ai/policies/{policy_id} | 422 | Get Policy | {"detail":[{"type":"int_parsing","loc":["path","policy_id"],"msg":"Input should  |
| PATCH | /api/ai/policies/{policy_id} | SKIPPED | Patch Policy | method PATCH not tested |
| PATCH | /api/ai/policies/{policy_id}/toggle | SKIPPED | Toggle Policy | method PATCH not tested |
| GET | /api/analytics/{region} | 200 | Get Analytics | {"region": "{region}", "sales": 12345, "revenue": 567890} |
| GET | /api/auth/pending-status | 200 | Get Pending Status | {"is_pending": false, "roles": ["admin", "user"], "message": "Your account is ac |
| POST | /api/auth/register | 422 | Register User | {"detail":[{"type":"missing","loc":["body","email"],"msg":"Field required","inpu |
| POST | /api/bundler/run | None | Run Bundler Job | timed out |
| GET | /api/contacts | 200 | List Contacts | [{"id": "003d6teEsgPckDX2AN", "first_name": "Jaya", "last_name": "Das", "email": |
| POST | /api/contacts/{contact_id}/draft | 500 | Draft Email | {"detail":"404: Contact not found"} |
| GET | /api/contacts/{contact_id}/emails | 404 | Get Contact Emails | {"detail":"Contact not found"} |
| GET | /api/dashboard/forecast | 200 | Get Revenue Forecast | {"forecast": "Unable to generate forecast at this time due to missing data or an |
| GET | /api/dashboard/stats | 200 | Get Dashboard Stats | {"total_leads": 296, "active_opportunities": 57, "pipeline_value": 15011577.0, " |
| GET | /api/data-manager/buying-groups | 200 | Get Buying Groups | {"buying_groups": [{"group_id": "BG-PENANG-01", "account_id": "001om06Dwt0Y3oobQ |
| GET | /api/data-manager/collisions | 200 | Get Engagement Collisions | {"count": 59, "collisions": [{"account_id": "001B6ICJ1JKEWzvaOw", "account_name" |
| GET | /api/data-manager/consent | 200 | Get Consent Registry | {"consent_records": [{"consent_id": "CNSo4nZRPjXTk9G", "contact_id": "003MZaoqMZ |
| GET | /api/data-manager/database/table/{table_name} | 404 | Get Db Table Data | {"detail":"Table not found"} |
| GET | /api/data-manager/database/tables | 200 | Get Db Tables | {"tables": ["alembic_version", "items", "settings", "audit_logs", "account", "bu |
| POST | /api/data-manager/database/upload | 422 | Upload Csv | {"detail":[{"type":"missing","loc":["query","table"],"msg":"Field required","inp |
| GET | /api/data-manager/dedup/config | 200 | Get Dedup Config | {"updated_by": "System", "id": 1, "confidence_threshold": 80.0, "updated_at": "2 |
| POST | /api/data-manager/dedup/config | 422 | Update Dedup Config | {"detail":[{"type":"missing","loc":["body","confidence_threshold"],"msg":"Field  |
| POST | /api/data-manager/dedup/run | 200 | Run Deduplication | {"results": {"merged": 0, "exceptions": 6, "details": [{"action": "exception", " |
| GET | /api/data-manager/integrations | 200 | Get Integrations | {"integrations": [{"name": "PostgreSQL Database", "type": "system_of_record", "s |
| GET | /api/data-manager/quality | 200 | Get Data Quality | {"chronological": [{"issue": "opportunity.closedate < opportunity.createddate",  |
| POST | /api/data-manager/quality/advise | 422 | Advise Quality Issue | {"detail":[{"type":"missing","loc":["body","category"],"msg":"Field required","i |
| POST | /api/data-manager/quality/fix | 200 | Fix Data Quality | {"status": "success", "message": "Data quality issues resolved"} |
| GET | /api/data-manager/quality/inspect | 422 | Inspect Quality Record | {"detail":[{"type":"missing","loc":["query","table"],"msg":"Field required","inp |
| POST | /api/data-manager/quality/update-record | 500 | Update Quality Record | {"detail":"400: Missing table, id, or fields"} |
| GET | /api/data-manager/routing | 200 | Get Routing Config | {"routing_rules": [{"rule_id": "RR-01", "region": "MY", "segment": "Enterprise", |
| POST | /api/data-manager/routing/run | 200 | Run Routing | {"results": {"assigned": 0, "exceptions": 0, "assignments": []}} |
| GET | /api/data-manager/search | 422 | Global Search | {"detail":[{"type":"missing","loc":["query","q"],"msg":"Field required","input": |
| GET | /api/data/{table_name} | 400 | Get Table Data | {"detail":"Table '{table_name}' not found. Allowed tables: account, buying_group |
| GET | /api/exceptions | 200 | List Exceptions | [{"type": "duplicate_contact", "severity": "warning", "title": "Possible duplica |
| POST | /api/exceptions | 422 | Create Exception | {"detail":[{"type":"missing","loc":["body","type"],"msg":"Field required","input |
| GET | /api/exceptions/stats | 200 | Exception Stats | {"total": 46, "by_status": {"pending": 46}, "by_severity": {"info": 3, "warning" |
| GET | /api/exceptions/{exception_id} | 422 | Get Exception | {"detail":[{"type":"int_parsing","loc":["path","exception_id"],"msg":"Input shou |
| PATCH | /api/exceptions/{exception_id}/resolve | SKIPPED | Resolve Exception | method PATCH not tested |
| GET | /api/files/ | 200 | List Files | {"files": [], "count": 0} |
| DELETE | /api/files/{file_path} | SKIPPED | Delete File | destructive; not tested |
| GET | /api/files/{file_path} | 500 | Download File | Internal Server Error |
| POST | /api/files/{file_path} | 422 | Upload File | {"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input |
| GET | /api/health | 200 | Read Health | {"status": "ok"} |
| GET | /api/insights | 200 | List Insights | [{"type": "anomaly", "severity": "critical", "title": "Mismatched Status Flags o |
| POST | /api/insights | 422 | Create Insight | {"detail":[{"type":"missing","loc":["body","type"],"msg":"Field required","input |
| GET | /api/insights/audit-trail | 200 | Get Audit Trail | {"count": 28, "trail": [{"insight_id": 49, "title": "Mismatched Status Flags on  |
| GET | /api/insights/forecast | 200 | Revenue Forecast | {"win_rate": 1.0, "open_pipeline": 15011577.0, "predicted_revenue": 15011577.0,  |
| POST | /api/insights/generate | None | Generate Insights | timed out |
| POST | /api/insights/self-learn | 200 | Self Learn | {"status": "success", "patterns_found": 0, "insights_created": 0, "insights": [] |
| GET | /api/insights/{insight_id}/trace | 422 | Get Insight Trace | {"detail":[{"type":"int_parsing","loc":["path","insight_id"],"msg":"Input should |
| GET | /api/items | 200 | List Items | [] |
| POST | /api/items | 422 | Create Item | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| DELETE | /api/items/{item_id} | SKIPPED | Delete Item | destructive; not tested |
| GET | /api/items/{item_id} | 422 | Get Item | {"detail":[{"type":"int_parsing","loc":["path","item_id"],"msg":"Input should be |
| PUT | /api/items/{item_id} | 422 | Update Item | {"detail":[{"type":"int_parsing","loc":["path","item_id"],"msg":"Input should be |
| POST | /api/llm/gemini | 422 | Call Gemini | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| POST | /api/llm/gemini/json | 422 | Call Gemini Json | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| POST | /api/llm/nemotron | 422 | Call Nemotron | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| GET | /api/llm/status | 200 | Llm Status | {"nvidia_nim": {"available": true, "model": "nvidia/nemotron-3-ultra-550b-a55b"} |
| POST | /api/operators/batch | 422 | Process Lead Batch | {"detail":[{"type":"list_type","loc":["body"],"msg":"Input should be a valid lis |
| POST | /api/operators/process | 200 | Process Single Lead | {"status": "success", "result": {"error": "400 Client Error: Bad Request for url |
| POST | /api/operators/run-all | None | Run Operators On All Contacts | timed out |
| GET | /api/permissions/matrix | 200 | Get Permission Matrix | {"matrix": {"admin": ["view_dashboard", "view_reports", "export_data", "create_p |
| POST | /api/permissions/matrix | 422 | Save Permission Matrix | {"detail":[{"type":"missing","loc":["body","matrix"],"msg":"Field required","inp |
| GET | /api/policies | 200 | List Policies | [{"name": "VIP Customer Ticket Escalation", "description": "", "natural_language |
| POST | /api/policies | 422 | Create Policy | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| POST | /api/policies/analyze | 422 | Analyze Policy | {"detail":[{"type":"missing","loc":["body","natural_language"],"msg":"Field requ |
| POST | /api/policies/check-conflicts | 200 | Check Conflicts | {"conflicts": [], "overrides": [], "clarifications": ["The new proposed policy t |
| POST | /api/policies/evaluate | 422 | Evaluate Policies | {"detail":[{"type":"missing","loc":["body","data"],"msg":"Field required","input |
| POST | /api/policies/generate | 422 | Generate Policy | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| POST | /api/policies/translate | 422 | Translate Policy | {"detail":[{"type":"missing","loc":["body","natural_language"],"msg":"Field requ |
| DELETE | /api/policies/{policy_id} | SKIPPED | Delete Policy | destructive; not tested |
| GET | /api/policies/{policy_id} | 422 | Get Policy | {"detail":[{"type":"int_parsing","loc":["path","policy_id"],"msg":"Input should  |
| PATCH | /api/policies/{policy_id} | SKIPPED | Patch Policy | method PATCH not tested |
| PUT | /api/policies/{policy_id} | 422 | Update Policy | {"detail":[{"type":"int_parsing","loc":["path","policy_id"],"msg":"Input should  |
| PATCH | /api/policies/{policy_id}/toggle | SKIPPED | Toggle Policy | method PATCH not tested |
| GET | /api/ready | 200 | Read Ready | {"status": "ready"} |
| GET | /api/secure-asset | 200 | Get Secure Asset | {"asset": "Top Secret Data", "accessed_from": "US"} |
| GET | /api/settings/ | 200 | Get Settings | {"approved_email_domains": "example.com"} |
| PUT | /api/settings/ | 422 | Update Settings | {"detail":[{"type":"missing","loc":["body","values"],"msg":"Field required","inp |
| GET | /api/test | 200 | Read Test Data | {"message": "Hello, dev-user"} |
| POST | /api/workbench/ask-ai | 422 | Ask Ai For Context | {"detail":[{"type":"missing","loc":["body","exception_id"],"msg":"Field required |
| POST | /api/workbench/draft-email | 422 | Draft Email | {"detail":[{"type":"missing","loc":["body","user_id"],"msg":"Field required","in |
| POST | /api/workbench/slack/block-kit | 422 | Generate Slack Block Kit | {"detail":[{"type":"missing","loc":["body","exception_id"],"msg":"Field required |

## Functional Feature Tests
| Feature | Endpoint | Status | Note |
|---------|----------|--------|------|
| Data Manager - buying-groups | /api/data-manager/buying-groups | 200 | data fetched |
| Data Manager - routing | /api/data-manager/routing | 200 | data fetched |
| Data Manager - consent | /api/data-manager/consent | 200 | data fetched |
| Data Manager - integrations | /api/data-manager/integrations | 200 | data fetched |
| Workbench - exceptions list | /api/exceptions | 200 | 46 items |
| AI Insights - list | /api/insights | 200 | 50 items |
| AI Insights - generate | /api/insights/generate | None | timed out |
| AI Policies - list | /api/policies | 200 | 4 items |
| Dashboard - stats | /api/dashboard/stats | 200 | stats fetched |
| Admin - /api/admin/users | /api/admin/users | 500 | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or  |
| Admin - /api/admin/roles | /api/admin/roles | 500 | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or  |
| Admin - /api/admin/groups | /api/admin/groups | 500 | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or  |
| Admin - /api/admin/sessions | /api/admin/sessions | 500 | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or  |
| Admin - /api/admin/events | /api/admin/events | 500 | {"detail":"501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or  |
| Admin - /api/admin/audit | /api/admin/audit | 200 | data fetched |
| Auth - pending status | /api/auth/pending-status | 200 | {"is_pending": false, "roles": ["admin", "user"], "message": "Your account is active."} |
| Data Pack - account | /api/data/account | 200 | 5 rows |
| Data Pack - buying_group | /api/data/buying_group | 200 | 5 rows |
| Data Pack - contact | /api/data/contact | 200 | 5 rows |

## Backend Unit Tests
```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /opt/venv/bin/python
cachedir: .pytest_cache
rootdir: /app
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 0 items

============================ no tests ran in 0.00s =============================
ERROR: file or directory not found: tests/test_main.py


```

## Backend Logs (last 30 lines)
```
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}
backend-1  | Failed to trigger Supervity Auto workflow: 400 Client Error: Bad Request for url: https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}
backend-1  | Failed to trigger Supervity Auto workflow: 400 Client Error: Bad Request for url: https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}
backend-1  | Failed to trigger Supervity Auto workflow: 400 Client Error: Bad Request for url: https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}
backend-1  | Failed to trigger Supervity Auto workflow: 400 Client Error: Bad Request for url: https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}
backend-1  | 172.19.0.1:36258 - "GET /api/policies HTTP/1.1" 200
backend-1  | 172.19.0.1:36266 - "GET /api/dashboard/stats HTTP/1.1" 200
backend-1  | Failed to list users: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:36268 - "GET /api/admin/users HTTP/1.1" 500
backend-1  | Failed to trigger Supervity Auto workflow: 400 Client Error: Bad Request for url: https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}
backend-1  | Failed to list roles: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:36276 - "GET /api/admin/roles HTTP/1.1" 500
backend-1  | Failed to get groups: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:36290 - "GET /api/admin/groups HTTP/1.1" 500
backend-1  | Failed to get sessions: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:36298 - "GET /api/admin/sessions HTTP/1.1" 500
backend-1  | Failed to get events: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:36308 - "GET /api/admin/events HTTP/1.1" 500
backend-1  | 172.19.0.1:36312 - "GET /api/admin/audit HTTP/1.1" 200
backend-1  | 172.19.0.1:36320 - "GET /api/auth/pending-status HTTP/1.1" 200
backend-1  | 172.19.0.1:36326 - "GET /api/data/account?limit=5 HTTP/1.1" 200
backend-1  | 172.19.0.1:36340 - "GET /api/data/buying_group?limit=5 HTTP/1.1" 200
backend-1  | 172.19.0.1:36352 - "GET /api/data/contact?limit=5 HTTP/1.1" 200
backend-1  | Failed to trigger Supervity Auto workflow: 400 Client Error: Bad Request for url: https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream
backend-1  | Response: {"error":"[\n  {\n    \"origin\": \"string\",\n    \"code\": \"invalid_format\",\n    \"format\": \"uuid\",\n    \"pattern\": \"/^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/\",\n    \"path\": [\n      \"workflowId\"\n    ],\n    \"message\": \"Invalid UUID\"\n  }\n]"}

```

## Frontend Logs (last 30 lines)
```
frontend-1  | 
frontend-1  | > autopilot-command-center@2.0.0 start
frontend-1  | > next start
frontend-1  | 
frontend-1  |    â–² Next.js 15.5.18
frontend-1  |    - Local:        http://localhost:3000
frontend-1  |    - Network:      http://172.19.0.4:3000
frontend-1  | 
frontend-1  |  âœ“ Starting...
frontend-1  |  âœ“ Ready in 602ms

```