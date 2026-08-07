# Supervity Inbound Revenue Command Center: Feature & Function List

This document outlines the complete set of features and functions built into both the Backend Orchestration layer and the Frontend Command Center.

## 🧠 Layer 1: The AI Agent (Supervity Auto + Python Backend)

### The Master Orchestrator
* **Function**: Coordinates the entire workflow. It acts as the central router, safely parsing the raw payload and governing the hand-offs between the 5 distinct Operator Agents without modifying variables natively.
* **Failure Handling**: Automatically halts the pipeline and routes exceptions to the human Workbench if any Operator flags an anomaly.

### The 5 Specialized Operators
1. **Intake & Verification Operator**: Validates the incoming payload to ensure no critical fields (like email or name) are missing before processing.
2. **Intent Scoring Operator**: Calculates an internal AI intent score and compares it against the external score to catch AI hallucinations or discrepancies.
3. **Privacy Compliance Operator**: Acts as a strict firewall. Checks the prospect's region against strict privacy laws (e.g., GDPR) and guarantees consent before outreach.
4. **Communication Operator**: Drafts and sends highly tailored outreach emails based on intent scores, running *only* if the previous 3 operators succeed perfectly.
5. **Reporting Operator**: Compiles a human-readable summary of the pipeline execution (success or failure) and pushes it to Slack.

---

## 🎛️ Layer 2: The Command Center (Frontend Template)

### Data Manager
* **Buying Group Resolution**: Automatically clusters scattered individual contacts into unified Account groups so sales reps pitch to the company, not isolated leads.
* **Adjustable Deduplication Engine**: Allows administrators to set an exact "Confidence Threshold" (e.g., 80%). The system auto-merges high-confidence duplicates and routes low-confidence conflicts to the Workbench.
* **Intelligent Capacity Routing**: Assigns incoming leads to SDRs based on territory, segment, and *live capacity*. Features a visual progress bar and catches overflow leads automatically.
* **Database Viewer**: A secure, read-only UI that allows administrators to inspect raw SQL tables directly from the frontend.

### The Workbench (The Safety Net)
* **Exception Inbox**: A central queue where the Orchestrator sends paused leads that require human review (e.g., Privacy mismatches, routing overflow).
* **AI-Assisted Resolution**: Every exception arrives pre-loaded with an `ai_recommendation` and `ai_confidence` score so the human operator can resolve complex issues instantly.

### AI Insights
* **Actionable Analytics**: Parses processed data to generate insights (like Revenue Forecasting or Competitor mentions).
* **One-Click Actions**: Insights are not static graphs; they provide action buttons that allow administrators to execute the AI's suggestions with a single click.

### AI Policies
* **Governed Rules engine**: Allows business leaders to enforce strict behavioral rules that natively constrain the Orchestrator and Operators (e.g., auto-merging specific domains).

### AI Manager
* **Conversational Interface**: A natural language chat UI wired directly to the backend database, allowing leaders to query lead status or records instantly.
