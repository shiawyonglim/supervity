# scripts/seed_policies.py
"""
Seed the database with default Sales Command Center policies.
Run this after the app starts to ensure there are always policies available.
"""

import os
import json
from sqlalchemy import create_engine, text
from datetime import datetime

DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/app_db")

SEED_POLICIES = [
    {
        "name": "Enterprise Lead Escalation",
        "description": "Escalate high-value enterprise leads with 500+ employees to VP for review.",
        "natural_language": "Escalate enterprise leads with more than 500 employees to VP for immediate review.",
        "summary": "Routes large enterprise prospects to VP-level attention.",
        "policy_type": "logical",
        "dsl": json.dumps({
            "conditions": [
                {"field": "NumberOfEmployees", "operator": "greater_than", "value": "500"},
                {"field": "Type", "operator": "equals", "value": "Prospect"}
            ],
            "actions": [
                {"type": "escalate", "value": "VP"},
                {"type": "flag", "value": "enterprise_lead"}
            ],
            "match_mode": "all"
        }),
        "refined_instruction": "When a prospect account has more than 500 employees, escalate to VP and flag as enterprise lead.",
        "ai_instruction": "Escalate enterprise leads with more than 500 employees to VP for immediate review.",
        "entity_name": "account",
        "is_active": True,
        "priority": 10,
        "tags": json.dumps(["enterprise", "escalation", "high-value"]),
    },
    {
        "name": "GDPR Email Compliance",
        "description": "Block automated emails to contacts in EU regions without explicit opt-in consent.",
        "natural_language": "Never send automated marketing emails to contacts in GDPR regions (Germany, France, UK, Spain, Italy) unless they have explicit opt-in consent.",
        "summary": "Prevents GDPR violations by blocking non-consented email outreach.",
        "policy_type": "natural_language",
        "dsl": None,
        "refined_instruction": "Before sending any automated email, check if the contact's billing country falls under GDPR jurisdiction. If so, verify that an active opt_in consent record exists for that contact. Block the email if no consent is found.",
        "ai_instruction": "Block automated emails to contacts in EU/GDPR regions without explicit opt-in consent.",
        "entity_name": "contact",
        "is_active": True,
        "priority": 5,
        "tags": json.dumps(["gdpr", "compliance", "email", "privacy"]),
    },
    {
        "name": "High-Intent Pricing Page Alert",
        "description": "Flag contacts who spend more than 5 minutes on the pricing page as hot leads.",
        "natural_language": "When a visitor spends more than 300 seconds on the /pricing page, flag them as a hot lead and notify the assigned SDR.",
        "summary": "Detects high buying intent from pricing page engagement.",
        "policy_type": "logical",
        "dsl": json.dumps({
            "conditions": [
                {"field": "url", "operator": "equals", "value": "/pricing"},
                {"field": "duration_seconds", "operator": "greater_than", "value": "300"}
            ],
            "actions": [
                {"type": "flag", "value": "hot_lead"},
                {"type": "notify", "value": "assigned_sdr"}
            ],
            "match_mode": "all"
        }),
        "refined_instruction": "When a visitor activity shows more than 300 seconds on the /pricing page, flag the associated prospect as a hot lead and trigger an SDR notification.",
        "ai_instruction": "Flag prospects spending over 5 minutes on pricing page as hot leads.",
        "entity_name": "visitoractivity",
        "is_active": True,
        "priority": 15,
        "tags": json.dumps(["intent", "pricing", "hot-lead", "notification"]),
    },
    {
        "name": "Missing Required Fields",
        "description": "Block saving CRM records that lack standard compliance fields.",
        "natural_language": "Reject any Contact record update that does not include a valid Title and Phone Number.",
        "summary": "Ensures CRM data quality by enforcing required fields.",
        "policy_type": "natural_language",
        "dsl": None,
        "refined_instruction": "Evaluate contact record payloads. If the 'Title' or 'Phone' fields are null, empty, or missing, reject the payload and return a validation error.",
        "ai_instruction": "Reject contact updates missing Title or Phone Number.",
        "entity_name": "contact",
        "is_active": True,
        "priority": 30,
        "tags": json.dumps(["data-quality", "compliance", "validation"]),
    },
    {
        "name": "Collision Detection",
        "description": "Prevent multiple sales reps from reaching out to the same company domain if there is an active Opportunity.",
        "natural_language": "If a contact's company domain matches an existing active opportunity owned by a different sales rep, flag it as a collision and prevent automated outreach.",
        "summary": "Prevents embarrassing overlapping outreach to the same company.",
        "policy_type": "natural_language",
        "dsl": None,
        "refined_instruction": "Evaluate the contact's company domain against the opportunity table. If an opportunity exists for that domain where IsClosed=False, flag the contact as 'collision_detected' and block outreach.",
        "ai_instruction": "Block outreach if the contact's company already has an open opportunity.",
        "entity_name": "contact",
        "is_active": True,
        "priority": 1,
        "tags": json.dumps(["collision", "account-based-sales", "routing"]),
    },
    {
        "name": "Stale Deal Alert",
        "description": "Flag opportunities with no activity in 14+ days as at-risk.",
        "natural_language": "Flag any opportunity that has been in the same stage for more than 14 days without activity as at-risk and notify the account owner.",
        "summary": "Identifies stalled deals that need attention.",
        "policy_type": "natural_language",
        "dsl": None,
        "refined_instruction": "Monitor opportunity records. If an opportunity's stage has not changed and there is no associated visitor activity or contact update for more than 14 days, mark it as at-risk and send a notification to the opportunity owner.",
        "ai_instruction": "Flag deals inactive for more than 14 days as at-risk.",
        "entity_name": "opportunity",
        "is_active": True,
        "priority": 20,
        "tags": json.dumps(["deal-health", "at-risk", "pipeline", "alert"]),
    },
    {
        "name": "Auto-Approve Small Deals",
        "description": "Auto-approve CRM updates for deals under $10,000.",
        "natural_language": "Auto-approve CRM updates for deals under $10,000 without requiring manager review.",
        "summary": "Speeds up pipeline for small deals by removing approval bottleneck.",
        "policy_type": "logical",
        "dsl": json.dumps({
            "conditions": [
                {"field": "Amount", "operator": "less_than", "value": "10000"}
            ],
            "actions": [
                {"type": "approve", "value": "auto"}
            ],
            "match_mode": "all"
        }),
        "refined_instruction": "When a deal/opportunity has an amount less than $10,000, auto-approve any CRM updates without requiring manager review.",
        "ai_instruction": "Auto-approve CRM updates for deals under $10,000.",
        "entity_name": "opportunity",
        "is_active": True,
        "priority": 30,
        "tags": json.dumps(["automation", "approval", "small-deals"]),
    },
]


def seed_policies():
    print("Connecting to database...")
    engine = create_engine(DB_URL)

    with engine.begin() as conn:
        # Check if policies already exist
        result = conn.execute(text("SELECT COUNT(*) FROM policies"))
        count = result.scalar()

        if count > 0:
            print(f"Found {count} existing policies. Skipping seed.")
            return

        print(f"Seeding {len(SEED_POLICIES)} default policies...")

        for policy_data in SEED_POLICIES:
            conn.execute(
                text("""
                    INSERT INTO policies (name, description, natural_language, summary, policy_type,
                                         dsl, refined_instruction, ai_instruction, entity_name,
                                         is_active, priority, tags, execution_count,
                                         created_at, updated_at)
                    VALUES (:name, :description, :natural_language, :summary, :policy_type,
                            :dsl, :refined_instruction, :ai_instruction, :entity_name,
                            :is_active, :priority, :tags, 0,
                            NOW(), NOW())
                """),
                policy_data,
            )
            print(f"  ✅ Created: {policy_data['name']}")

    print(f"\n🎉 Successfully seeded {len(SEED_POLICIES)} policies!")


if __name__ == "__main__":
    seed_policies()
