# Supervity Website Test Report

Generated: 2026-08-05T11:15:52.618451Z

## Executive Summary
- Frontend build: passing
- Backend build: passing
- Frontend routes tested: 16
- Backend endpoints discovered: 95
- Functional features tested: 19
- Frontend route failures: 0
- Functional feature failures: 6

## Container Status
```
NAME                   IMAGE                COMMAND                  SERVICE    CREATED         STATUS                   PORTS
supervity-backend-1    supervity-backend    "sh start_gunicorn.sh"   backend    5 minutes ago   Up 2 minutes (healthy)   127.0.0.1:8001->8000/tcp
supervity-frontend-1   supervity-frontend   "docker-entrypoint.sâ€¦"   frontend   4 minutes ago   Up 2 minutes (healthy)   127.0.0.1:3001->3000/tcp
supervity-postgres-1   postgres:15-alpine   "docker-entrypoint.sâ€¦"   postgres   21 hours ago    Up 2 hours (healthy)     0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp

```

## Frontend Routes
| Route | Source | Status | Length | Error Text |
|-------|--------|--------|--------|------------|
| / | C:/supervity/supervity/frontend/src/app/page.tsx | 200 | 89043 | no |
| /admin/audit | C:/supervity/supervity/frontend/src/app/admin/audit/page.tsx | 200 | 34653 | no |
| /admin/events | C:/supervity/supervity/frontend/src/app/admin/events/page.tsx | 200 | 27942 | no |
| /admin/groups | C:/supervity/supervity/frontend/src/app/admin/groups/page.tsx | 200 | 27820 | no |
| /admin/roles | C:/supervity/supervity/frontend/src/app/admin/roles/page.tsx | 200 | 46850 | no |
| /admin/sessions | C:/supervity/supervity/frontend/src/app/admin/sessions/page.tsx | 200 | 27834 | no |
| /admin/settings | C:/supervity/supervity/frontend/src/app/admin/settings/page.tsx | 200 | 46970 | no |
| /admin/users | C:/supervity/supervity/frontend/src/app/admin/users/page.tsx | 200 | 95572 | no |
| /ai/insights | C:/supervity/supervity/frontend/src/app/ai/insights/page.tsx | 200 | 59954 | no |
| /ai/policies | C:/supervity/supervity/frontend/src/app/ai/policies/page.tsx | 200 | 37657 | no |
| /auth/error | C:/supervity/supervity/frontend/src/app/auth/error/page.tsx | 200 | 9366 | no |
| /auth/register | C:/supervity/supervity/frontend/src/app/auth/register/page.tsx | 200 | 23064 | no |
| /auth/signin | C:/supervity/supervity/frontend/src/app/auth/signin/page.tsx | 200 | 9423 | no |
| /data-manager | C:/supervity/supervity/frontend/src/app/data-manager/page.tsx | 200 | 29279 | no |
| /settings | C:/supervity/supervity/frontend/src/app/settings/page.tsx | 200 | 43748 | no |
| /workbench | C:/supervity/supervity/frontend/src/app/workbench/page.tsx | 200 | 40464 | no |

## Backend API Smoke Tests
| Method | Path | Status | Summary | Response Snippet |
|--------|------|--------|---------|------------------|
| GET | / | 200 | Root | {"name": "AutoPilot API", "version": "2.0.0", "docs": "/api/docs", "health": "/a |
| GET | /api/admin/audit | 200 | List Audit Logs | {"logs": [{"id": 133, "timestamp": "2026-08-05T11:15:49.241629Z", "actor_id": nu |
| GET | /api/admin/audit/actions | 200 | List Audit Actions | {"actions": ["user.approve", "api.get", "api.delete.admin.users", "api.get.admin |
| GET | /api/admin/audit/actor/{actor_email} | 200 | Get Actor Audit Trail | {"actor_email": "{actor_email}", "logs": [], "total": 0, "page": 1, "page_size": |
| GET | /api/admin/audit/categories | 200 | List Audit Categories | {"categories": ["settings", "user_management", "api", "auth", "admin"]} |
| GET | /api/admin/audit/export | 200 | Export Audit Logs | ID,Timestamp,Actor Email,Actor IP,Action,Category,Severity,Resource Type,Resourc |
| GET | /api/admin/audit/resource/{resource_type}/{resource_id} | 200 | Get Resource Audit Trail | {"resource_type": "{resource_type}", "resource_id": "{resource_id}", "logs": [], |
| GET | /api/admin/audit/stats | 200 | Get Audit Stats | {"total_events": 133, "events_today": 114, "events_this_week": 133, "by_category |
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
| GET | /api/analytics/{region} | 200 | Get Analytics | {"region": "{region}", "sales": 12345, "revenue": 567890} |
| GET | /api/auth/pending-status | 200 | Get Pending Status | {"is_pending": false, "roles": ["admin", "user"], "message": "Your account is ac |
| POST | /api/auth/register | 422 | Register User | {"detail":[{"type":"missing","loc":["body","email"],"msg":"Field required","inpu |
| GET | /api/dashboard/stats | 200 | Get Dashboard Stats | {"total_leads": 296, "active_opportunities": 57, "pipeline_value": 15011577.0, " |
| GET | /api/data-manager/buying-groups | 200 | Get Buying Groups | {"buying_groups": [{"group_id": "BG-PENANG-01", "account_id": "001om06Dwt0Y3oobQ |
| GET | /api/data-manager/consent | 200 | Get Consent Registry | {"consent_records": [{"consent_id": "CNSo4nZRPjXTk9G", "contact_id": "003MZaoqMZ |
| GET | /api/data-manager/integrations | 200 | Get Integrations | {"integrations": [{"name": "PostgreSQL Database", "type": "system_of_record", "s |
| GET | /api/data-manager/routing | 200 | Get Routing Config | {"routing_rules": [{"rule_id": "RR-01", "region": "MY", "segment": "Enterprise", |
| GET | /api/data/{table_name} | 400 | Get Table Data | {"detail":"Table '{table_name}' not found. Allowed tables: account, buying_group |
| GET | /api/exceptions | 200 | List Exceptions | [] |
| POST | /api/exceptions | 422 | Create Exception | {"detail":[{"type":"missing","loc":["body","type"],"msg":"Field required","input |
| GET | /api/exceptions/stats | 200 | Exception Stats | {"total": 0, "by_status": {}, "by_severity": {}} |
| GET | /api/exceptions/{exception_id} | 422 | Get Exception | {"detail":[{"type":"int_parsing","loc":["path","exception_id"],"msg":"Input shou |
| PATCH | /api/exceptions/{exception_id}/resolve | SKIPPED | Resolve Exception | method PATCH not tested |
| GET | /api/files/ | 200 | List Files | {"files": [], "count": 0} |
| DELETE | /api/files/{file_path} | SKIPPED | Delete File | destructive; not tested |
| GET | /api/files/{file_path} | 500 | Download File | Internal Server Error |
| POST | /api/files/{file_path} | 422 | Upload File | {"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input |
| GET | /api/health | 200 | Read Health | {"status": "ok"} |
| GET | /api/insights | 200 | List Insights | [] |
| POST | /api/insights | 422 | Create Insight | {"detail":[{"type":"missing","loc":["body","type"],"msg":"Field required","input |
| POST | /api/insights/generate | 500 | Generate Insights | {"detail":"429 You exceeded your current quota, please check your plan and billi |
| GET | /api/items | 200 | List Items | [] |
| POST | /api/items | 422 | Create Item | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| DELETE | /api/items/{item_id} | SKIPPED | Delete Item | destructive; not tested |
| GET | /api/items/{item_id} | 422 | Get Item | {"detail":[{"type":"int_parsing","loc":["path","item_id"],"msg":"Input should be |
| PUT | /api/items/{item_id} | 422 | Update Item | {"detail":[{"type":"int_parsing","loc":["path","item_id"],"msg":"Input should be |
| POST | /api/llm/gemini | 422 | Call Gemini | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| POST | /api/llm/gemini/json | 422 | Call Gemini Json | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| POST | /api/llm/nemotron | 422 | Call Nemotron | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| GET | /api/llm/status | 200 | Llm Status | {"nvidia_nim": {"available": true, "model": "nvidia/nemotron-3-ultra-550b-a55b"} |
| GET | /api/policies | 200 | List Policies | [] |
| POST | /api/policies | 422 | Create Policy | {"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input |
| POST | /api/policies/generate | 422 | Generate Policy | {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","inp |
| DELETE | /api/policies/{policy_id} | SKIPPED | Delete Policy | destructive; not tested |
| GET | /api/policies/{policy_id} | 422 | Get Policy | {"detail":[{"type":"int_parsing","loc":["path","policy_id"],"msg":"Input should  |
| PUT | /api/policies/{policy_id} | 422 | Update Policy | {"detail":[{"type":"int_parsing","loc":["path","policy_id"],"msg":"Input should  |
| PATCH | /api/policies/{policy_id}/toggle | SKIPPED | Toggle Policy | method PATCH not tested |
| GET | /api/ready | 200 | Read Ready | {"status": "ready"} |
| GET | /api/secure-asset | 200 | Get Secure Asset | {"asset": "Top Secret Data", "accessed_from": "US"} |
| GET | /api/test | 200 | Read Test Data | {"message": "Hello, dev-user"} |

## Functional Feature Tests
| Feature | Endpoint | Status | Note |
|---------|----------|--------|------|
| Data Manager - buying-groups | /api/data-manager/buying-groups | 200 | data fetched |
| Data Manager - routing | /api/data-manager/routing | 200 | data fetched |
| Data Manager - consent | /api/data-manager/consent | 200 | data fetched |
| Data Manager - integrations | /api/data-manager/integrations | 200 | data fetched |
| Workbench - exceptions list | /api/exceptions | 200 | 0 items |
| AI Insights - list | /api/insights | 200 | 0 items |
| AI Insights - generate | /api/insights/generate | 500 | {"detail":"429 You exceeded your current quota, please check your plan and billing details. For more |
| AI Policies - list | /api/policies | 200 | 0 items |
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
backend-1  |     key: "model"
backend-1  |     value: "gemini-2.0-flash"
backend-1  |   }
backend-1  |   quota_dimensions {
backend-1  |     key: "location"
backend-1  |     value: "global"
backend-1  |   }
backend-1  | }
backend-1  | , retry_delay {
backend-1  |   seconds: 11
backend-1  | }
backend-1  | ]
backend-1  | 172.19.0.1:47540 - "POST /api/insights/generate HTTP/1.1" 500
backend-1  | 172.19.0.1:47542 - "GET /api/policies HTTP/1.1" 200
backend-1  | 172.19.0.1:47558 - "GET /api/dashboard/stats HTTP/1.1" 200
backend-1  | Failed to list users: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:47560 - "GET /api/admin/users HTTP/1.1" 500
backend-1  | Failed to list roles: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:47566 - "GET /api/admin/roles HTTP/1.1" 500
backend-1  | Failed to get groups: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:47570 - "GET /api/admin/groups HTTP/1.1" 500
backend-1  | Failed to get sessions: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:47576 - "GET /api/admin/sessions HTTP/1.1" 500
backend-1  | Failed to get events: 501: User management requires Keycloak. Set AUTH_BYPASS=false and configure Keycloak, or re-add keycloak_admin service.
backend-1  | 172.19.0.1:47590 - "GET /api/admin/events HTTP/1.1" 500
backend-1  | 172.19.0.1:47598 - "GET /api/admin/audit HTTP/1.1" 200
backend-1  | 172.19.0.1:47602 - "GET /api/auth/pending-status HTTP/1.1" 200
backend-1  | 172.19.0.1:47606 - "GET /api/data/account?limit=5 HTTP/1.1" 200
backend-1  | 172.19.0.1:47616 - "GET /api/data/buying_group?limit=5 HTTP/1.1" 200
backend-1  | 172.19.0.1:47622 - "GET /api/data/contact?limit=5 HTTP/1.1" 200

```

## Frontend Logs (last 30 lines)
```
frontend-1  | 
frontend-1  | > autopilot-command-center@2.0.0 start
frontend-1  | > next start
frontend-1  | 
frontend-1  |    â–² Next.js 15.5.18
frontend-1  |    - Local:        http://localhost:3000
frontend-1  |    - Network:      http://172.19.0.3:3000
frontend-1  | 
frontend-1  |  âœ“ Starting...
frontend-1  |  âœ“ Ready in 794ms

```