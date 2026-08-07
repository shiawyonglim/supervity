# Supervity Workflow Architecture

## 1. Master Orchestrator
* **Role**: Coordinates the entire workflow. 
* **Function**: Since Supervity cannot handle complex comparisons or simple variable passing, the Orchestrator manages the hand-offs. It ensures data is routed to external pre-processing for calculations, and then passes that finalized info to the downstream Operators.

## 2. The 5 Operators

**Operator 1: Intake & Verification Operator**
* *Action*: Reads the initial data sent to Supervity. If there are missing values, it asks for user input using Slack.

**Operator 2: Intent Scoring Operator**
* *Action*: Calculates the user's intent score and double-checks if it matches the score received from the external calculation.
* *Fallback*: If the calculated score does not match the received score, it asks a human to review it via Slack.

**Operator 3: Privacy Compliance Operator**
* *Action*: Double-checks privacy laws and regulations. Returns `true` or `false` (compliance flag) back to Supervity.
**Operator 4: Communication Operator**
* *Action*: Drafts and sends the email using the pre-calculated intent score and privacy data.

**Operator 5: Reporting Operator**
* *Action*: Compiles a summary report and tells the user through Slack exactly what the AI has done.