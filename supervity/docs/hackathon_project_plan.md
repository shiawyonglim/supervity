# 🚀 Hackathon Project Plan: Inbound Revenue Command Center

This document expands on your initial 8-point checklist to provide actionable, detailed steps for building out your Command Center.

## 1. 🧠 Integrate the LLMs (Dual-Model Strategy)
*Your backend needs a brain to power Policies, Insights, and data analysis. You are using the dual-model strategy for maximum bonus points.*
- [ ] **API Setup:** Add your `GEMINI_API_KEY` and `NVIDIA_NIM_API_KEY` to your `.env` file.
- [ ] **Base Service:** Create a core LLM service class (e.g., `app/services/llm_service.py`) that handles sending prompts and routing requests between Gemini and Nemotron.
- [ ] **Gemini (AI Insights & Analytics):** Use Gemini's massive context window and native JSON mode/structured outputs to analyze large batches of messy database records to generate your AI Insights (Patterns, Anomalies, Recommendations).
- [ ] **Nemotron 550B (AI Policies):** Use NVIDIA NIM's Nemotron 550B to parse complex natural language and translate it into strict backend IF/THEN rules for your Policy Engine. This proves enterprise-scale open-source capabilities to the judges.

## 2. 💾 Seed the Data
*The foundation of the system. (✅ You already completed this!)*
- [x] Load `Account`, `Contact`, `VisitorActivity`, and other CSVs into the PostgreSQL database.
- [x] Verify relationships (e.g., contacts map to accounts, territories map to SDRs).

## 3. 🤖 Build the 5 Operators (on auto.supervity.ai)
*The specialist workers. These MUST be built on the Auto platform, not in code.*
- [ ] **Operator 1 (Lead Deduplicator & Resolver):** Identifies if a new visitor is a duplicate or part of an existing buying group.
- [ ] **Operator 2 (Consent & Privacy Checker):** Checks the `consent_register` to ensure we are legally allowed to reach out based on region.
- [ ] **Operator 3 (Lead Scorer):** Uses `icp_scoring_config` to evaluate lead quality.
- [ ] **Operator 4 (Router):** Uses `routing_rules` and `territories` to assign the lead to the correct sales rep.
- [ ] **Operator 5 (Outreach Drafter):** Drafts a highly personalized email context for the sales rep.
- [ ] **API Integration:** For each operator, define "Tools" (API webhooks) on the Auto platform that point to your backend endpoints to fetch/update database records.

## 4. 🧠 Setup AI Manager / Orchestrator (on auto.supervity.ai)
*The boss of the operators.*
- [ ] **Create the Agent:** Create a master Orchestrator agent on the Auto platform.
- [ ] **Define Routing Logic:** Give it prompt instructions on the sequence of events (e.g., "When a webhook triggers for a new visitor, first call Deduplicator, then Consent Checker...").
- [ ] **Define Exceptions:** Explicitly tell the Orchestrator: "If an operator fails, if confidence is low, or if a Policy is violated, STOP and send the payload to the Workbench Exception Queue."

## 5. 🛠️ Setup Workbench (Exception Handling)
*Where humans handle what the AI cannot.*
- [ ] **Backend Queue:** Create a database table/model for `Exceptions` or `Tasks` (status: pending, resolved).
- [ ] **UI - Task Queue:** Build a list view in `frontend/src/app/workbench/` showing pending exceptions with priority tags (High, Medium, Low).
- [ ] **UI - Quick Actions:** Add "Approve", "Reject", and "Modify" buttons for human operators to quickly resolve data conflicts.
- [ ] **UI - AI Assistant:** A chat sidebar where the human can ask the AI "Why did this fail?" or "Summarize this lead's history."
- [ ] **UI - Automation Builder:** A button that says "Don't show this again" which converts a manual human resolution into a new AI Policy.

## 6. 📜 AI Policies (The Guardrails)
*Rules that constrain the AI. Currently missing backend logic.*
- [ ] **Backend - DB Models:** Create a `policies` table (fields: name, description, condition, action, status, created_by).
- [ ] **Backend - CRUD API:** Build FastAPI endpoints to Create, Read, Update, and Delete policies.
- [ ] **UI - Create with AI:** A text box where a user types "Never email EU residents on weekends." The backend LLM parses this natural language into a structured rule.
- [ ] **UI - Structured Builder:** A fallback UI with dropdowns (IF [Region] [equals] [EU] THEN [Action] [Require Approval]).
- [ ] **UI - Permission Matrix:** A view showing who is allowed to edit or approve policies (e.g., Admin vs. Standard Rep).

## 7. 💡 AI Insights (Visibility)
*Displaying what the AI is thinking and finding.*
- [ ] **Backend - Analysis Engine:** Create a script (or scheduled task) that pulls recent database activity and asks the LLM to find patterns (e.g., "Are there any anomalies in lead volume?").
- [ ] **UI - Dashboard:** Build the UI in `frontend/src/app/ai/insights/`.
- [ ] **Categorization:** Visually separate insights into three buckets: 
      1. **Patterns** (Recurring behaviors)
      2. **Anomalies** (Spikes or weird behavior)
      3. **Recommendations** (Actionable suggestions to create new policies).

## 8. 🗄️ Data Manager 
*Handling, cleaning, and organizing messy data.*
- [ ] **Backend APIs:** Expose endpoints for Accounts, Buying Groups, and Routing Rules.
- [ ] **UI - Buying Group View:** A page showing which isolated contacts have been grouped into single "Buying Groups."
- [ ] **UI - Routing Configuration:** A visual table or map showing `territories` and `sdr_roster` rules.
- [ ] **UI - Deduplication Rules:** A settings panel to determine how strict the deduplication matching should be (e.g., "Exact Email Match" vs. "Fuzzy Name + Company Match").
