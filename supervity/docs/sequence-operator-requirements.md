# Sequence Orchestration Operator — Requirements

For building directly in the Supervity Auto workflow builder. Written as a functional
spec, not code — map each section onto whatever fields Auto's builder exposes
(name/description, tools/integrations, trigger, guardrails, etc).

## Purpose

Given a contact, determine which outreach sequence (if any) they're eligible for based on
their current lead stage, and manage sending the sequence's touches at the correct
cadence — WITHOUT ever guessing when the data is ambiguous.

## Trigger

Runs after a contact's `lead_stage__c` is set or changes — either as a step in the
existing 5-operator pipeline (after Route, before/alongside Outreach Draft) or on its own
trigger whenever stage changes. Confirm with your team whether this is a new step
appended to the existing workflow_id pipeline, or a separate workflow — structurally
simpler to add as a step in the existing one if the platform supports branching there.

## Inputs (per contact)

- `contact_id`
- `lead_stage__c` (current value: Open / MQL / SQL / Opportunity / Customer)
- `region` (for the consent check)
- Whether they're already mid-sequence (touch progress) — needs a place to persist this;
  see "State to track" below.

## Core logic

1. **Look up active sequences matching the contact's stage.** Reference data (already
   seeded, confirm still current before building against it):

   | Stage | Active sequence(s) | Touches | Channel | Wait between touches |
   |---|---|---|---|---|
   | Open | SEQ-04 Trade-Show Nurture | 4 | email | 4 days |
   | MQL | SEQ-01 Inbound High-Intent MY | 5 | email | 2 days |
   | SQL | SEQ-02 Pricing-Page Fast Follow **AND** SEQ-06 Enterprise Exec Outreach | 3 / 5 | email / multi | 1 day / 3 days |
   | Opportunity | SEQ-03 Buying-Group Account Play | 6 | multi | 3 days |
   | Customer | none | — | — | — |

   Never match an inactive sequence (SEQ-05 exists for MQL but is inactive — exclude it).

2. **Zero matches (Customer stage):** do not enroll, do not error. This may be intentional
   (no nurture needed for existing customers) — just don't silently drop these contacts
   from any reporting; they should show up as "no eligible sequence" somewhere visible,
   not disappear.

3. **Exactly one match:** proceed to the consent gate (step 4), then enroll.

4. **Two or more matches (currently only SQL):** do NOT auto-pick one. This needs either:
   - a `priority` value added to the sequence config (if your team decides one sequence
     should always win for a given case — e.g. by account segment/size), or
   - a human decision via the Workbench.

   If routing to the Workbench, call the existing exception API — this is a real,
   already-working endpoint, wire it exactly like this:

   ```
   POST /api/exceptions
   {
     "type": "policy_conflict",
     "severity": "warning",
     "title": "Multiple active sequences match SQL stage",
     "description": "Contact <contact_id> is SQL-stage; SEQ-02 and SEQ-06 both match with no priority set.",
     "prospect_id": "<contact_id>",
     "context": {
       "candidates": [
         {"sequence_id": "SEQ-02", "channel": "email", "touches": 3, "wait_days": 1},
         {"sequence_id": "SEQ-06", "channel": "multi", "touches": 5, "wait_days": 3}
       ]
     },
     "ai_recommendation": "<your suggested pick and why, e.g. 'SEQ-06 — account is Enterprise segment'>",
     "ai_confidence": <0-100>
   }
   ```
   Do not enroll the contact in either sequence until a human resolves this (via
   `PATCH /api/exceptions/{id}/resolve`).

5. **Consent gate — check before EVERY touch, not just at enrollment.** A contact can be
   validly enrolled and then have consent change mid-sequence (e.g. they unsubscribe after
   touch 2) — re-check before each send, don't just check once at the start. Required:
   - `Contact.HasOptedOutOfEmail = false` AND `Contact.DoNotCall = false` for the relevant
     channel(s), AND
   - an `active` record in `Consent_Register` for that contact covering the applicable
     region. If the contact has multiple, conflicting-region consent records, treat this
     the same as the SQL-collision case — don't guess, escalate.
   - If consent fails at any point mid-sequence, stop sending remaining touches. Don't
     resume automatically if consent is later restored — that should be a fresh decision.

6. **Send loop, once enrollment + consent are both clear:**
   - Send touch 1.
   - Wait `wait_days` (per the sequence's own value, not a fixed number).
   - Re-check consent (step 5).
   - Send touch 2. Repeat until `steps`/`num_touches` is reached.
   - This is the part that should actually live in Auto's own scheduling/workflow
     capability — don't build a custom timer/queue elsewhere if Auto already has a
     wait/delay primitive.

## State to track (per contact, per sequence)

- Which sequence they're enrolled in
- Which touch number they're currently on
- Enrollment timestamp, last-touch timestamp
- If paused (consent failure) vs completed vs actively running

This needs to live somewhere queryable — either a table your backend exposes (recommended:
simplest is a small `sequence_enrollments` table your existing FastAPI backend can own,
with the Operator calling it as a tool to read/update state) or Auto's own persistent
workflow state, if the platform supports that natively for long-running, multi-day flows.
Decide based on what Auto actually offers for multi-day waits — check the platform docs
before assuming a custom table is needed.

## Guardrails (do not violate)

- Never invent a value for a missing field (e.g. don't guess a region if it's blank —
  escalate instead).
- Never send a touch without a fresh consent check immediately before that specific send.
- Never auto-resolve the SQL two-sequence collision — always escalate until a priority
  rule exists.
- Every enrollment, every touch sent, and every escalation should be logged with enough
  context to reconstruct why it happened (sequence_id, stage at time of decision,
  consent-check result) — this feeds your audit trail and AI Insights, and is part of
  what's actually graded ("every evaluation logged").

## Out of scope for this Operator

- Drafting the actual message content — that's the separate Outreach Draft step.
- Deciding lead stage itself — this Operator only reads `lead_stage__c`, it never writes
  it.
- Building any new frontend page — sequence status/eligibility should surface as a
  card/tab inside the existing Data Manager page if you want it visible there, not a new
  route.
