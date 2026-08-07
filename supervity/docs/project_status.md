# Supervity Hackathon Project Status

This document tracks the progress of the hackathon project based on the original requirements list. 

## ✅ What is DONE

1. **Integrate the LLM**
   - Successfully integrated **NVIDIA NIM (Nemotron-3-ultra-550b)** for AI Policy generation.
   - Successfully integrated **Google Gemini (gemini-flash-latest)** for AI Insights and data analytics.
   - Implemented automatic **Gemini → NVIDIA NIM fallback** with a user-facing notice when the primary model is unavailable.

2. **Seed the Data**
   - Database is seeded with mock CRM data (Contacts, Accounts, Opportunities).
   - SQL tables auto-initialize on FastAPI startup.

3. **Fix the Main Dashboard**
   - Frontend `page.tsx` is successfully wired to the backend `/api/dashboard/stats`.
   - Live KPIs (Total Leads, Active Opportunities, Win Rate, Active Policies) are now displaying real data.

4. **AI Policies (Add rules for the AI)**
   - **Backend:** Created Pydantic schemas, SQLAlchemy models, and FastAPI routers for Policies.
   - **Frontend:** Wired the Policies page (`/ai/policies`) to the backend.
   - **Create with AI:** Implemented the integration for generating policies using the LLM.
   - **Policies List:** Fully functional CRUD operations (view, create, toggle status, delete).
   - **Permission Matrix:** Backend endpoints (`/api/permissions/matrix`) persist role/permission mappings and the frontend Permission Matrix tab now loads and saves them.

5. **AI Insight (Display what the AI is thinking)**
   - **Backend Analyzer:** Created the `/api/insights/generate` endpoint using Google Gemini to analyze CRM data and output structured JSON.
   - **The Dashboard:** Wired the Insights page (`/ai/insights`) to display Patterns and Action Items dynamically based on the AI's analysis.
   - **Self-Learning:** Added `/api/insights/self-learn` to scan resolved exceptions and auto-suggest AI Policies.
   - **Deep Auditability:** Insight generation now records a step-by-step `ai_trace`; added `/api/insights/{id}/trace` and `/api/insights/audit-trail` endpoints plus a "View AI Trace" control in the frontend `InsightCard`.

6. **Workbench (For handling error)**
   - **Exception Inbox:** Built an "Exception Inbox" in the Workbench to review and resolve automated tasks that require human intervention.
   - **AI Assistant:** Added a dedicated `AI Assistant` chat tab in the Workbench that uses the AI Manager orchestrator (`/api/ai/chat`).
   - **Quick Actions:** Wired the Workbench Quick Actions card so users can run Generate Insights, Self-Learn, Deduplication, Collision Detection, and Revenue Forecast directly from the Workbench.
   - Wired the UI to the backend `/api/exceptions` and resolution endpoints.
   - Added backend `/api/workbench/ask-ai` and `/api/workbench/draft-email` for contextual AI help and prospect email drafting.

7. **Data Manager (Handle, clean, and organize messy data)**
   - Created the `/data-manager` page from scratch.
   - **Buying Group Resolution:** Implemented the backend endpoint and frontend UI to group contacts by Accounts and display their roles.
   - Implemented tabs for Routing & Territories, Consent Registry, and Integrations (showing the live status of the LLMs and databases).
   - **Data Quality Dashboard:** Built a comprehensive data quality checker (`/api/data-manager/quality`) that scans for missing values, exact/PK duplicates, date format inconsistencies, business logic anomalies (like over-capacity SDRs), and explicitly traps dangling foreign keys.
   - **Collision Detection:** Added `/api/data-manager/collisions` to detect when multiple reps are actively engaging contacts at the same account.

8. **AI Manager / 5 Operators**
   - Backend `ai_chat.py` orchestrates tools: `get_dashboard_stats`, `get_pending_exceptions`, `get_active_policies`, `get_revenue_forecast`, and `get_deduplication_summary`.
   - The Workbench chat uses this orchestrator, and each tool is an independent "operator" that runs deterministically against the database.

9. **Loop the Whole Dataset**
   - Registered the `/api/operators` router and added `/api/operators/run-all`, which fetches every contact and runs the 5-step operator pipeline in batches.

10. **Settings**
    - Backend `settings` router exposes `/api/settings` (GET/PUT) for key-value settings.
    - The Settings page quick toggles are now wired to load from and save to the backend.

11. **Search**
    - Added `/api/data-manager/search` that searches contacts, accounts, and opportunities.
    - The Command Palette now fetches live CRM results as the user types and handles navigation/action handlers (diagnostics, help, new-task, refresh).

12. **Upload Data to the Database**
    - Added `/api/data-manager/database/upload` for CSV uploads into any table.
    - The Data Manager Database tab now has an "Upload CSV" button per table.

13. **Data Quality AI Advisor**
    - Added `/api/data-manager/quality/advise` that uses an LLM to explain a data quality issue and list concrete remediation steps.
    - The Data Manager quality report items have an "Ask AI" button that opens the advice in a dialog.

14. **Automation Builder**
    - Added an "Automation Builder" tab to the Workbench where users can build if/then rules and save them as AI Policies.

---

## 🚧 What is NOT DONE YET (Pending / Work in Progress)

1. **Deduplication Physical Merge**
   - The deduplication engine routes low-confidence groups to the Workbench as exceptions. A safe, FK-aware physical merge/delete for high-confidence groups is a future enhancement.

2. **Admin Endpoints**
   - Several `/api/admin/*` endpoints return 501/500 because Keycloak is not configured in the local Docker environment. These are not part of the hackathon features and work once Keycloak is wired.

---

## 🏗️ Architecture: Frontend and Backend Connection

The Next.js frontend (React) and FastAPI backend (Python) are connected using a unified API client pattern:

1. **The `apiClient` Utility (`frontend/src/lib/api-client.ts`)**
   - The frontend uses a custom wrapper around the native `fetch` API.
   - When a component calls `apiClient.get('/api/endpoint')`, it dynamically prepends the `NEXT_PUBLIC_API_URL` environment variable.
   - Example: A call to `/api/dashboard/stats` is routed to `http://localhost:8001/api/dashboard/stats`.

2. **CORS Middleware**
   - Because the frontend and backend run on different ports (`3001` vs `8001`), the FastAPI backend in `app/main.py` is configured with `CORSMiddleware`.
   - This ensures the browser doesn't block cross-origin requests from the React application.

3. **Docker Networking**
   - When running via Docker Compose (`run_docker.bat`), both apps run in the same internal network but are exposed to the host on their respective ports. The `apiClient` seamlessly facilitates the communication between the browser and the FastAPI server.

---
*Last Updated: August 7, 2026*
