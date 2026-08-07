@router.get("/quality")
def get_data_quality(db: Session = Depends(get_db)):
    """Run comprehensive data quality checks on DB and return results."""
    from app.models.exception import Exception as ExceptionModel
    import pandas as pd
    
    report = {
        "chronological": [],
        "relational": [],
        "state_logic": [],
        "format": []
    }

    def add_to_report(category, issue, count, severity, examples=None):
        if count > 0:
            report[category].append({
                "issue": issue,
                "count": count,
                "severity": severity,
                "examples": examples or []
            })
            
            exc_exists = db.query(ExceptionModel).filter(
                ExceptionModel.type == "data_quality_anomaly",
                ExceptionModel.title == issue
            ).first()
            if not exc_exists:
                db.add(ExceptionModel(
                    type="data_quality_anomaly",
                    title=issue,
                    description=f"Data quality check found {count} affected rows. Check examples.",
                    context={"examples": examples or []},
                    severity=severity
                ))

    # Chronological checks
    res = db.execute(text('SELECT "Id" FROM opportunity WHERE CAST("CloseDate" AS DATE) < CAST("CreatedDate" AS DATE)')).fetchall()
    add_to_report("chronological", "opportunity.closedate < opportunity.createddate", len(res), "warning", [r[0] for r in res[:5]])
    
    res = db.execute(text('SELECT "Id" FROM contact WHERE CAST("LastModifiedDate" AS DATE) < CAST("CreatedDate" AS DATE)')).fetchall()
    add_to_report("chronological", "contact.lastmodifieddate < contact.createddate", len(res), "warning", [r[0] for r in res[:5]])
    
    res = db.execute(text('SELECT "Id" FROM opportunity WHERE ("IsClosed" = \'True\' OR "IsClosed" = \'true\') AND CAST("CloseDate" AS DATE) > CURRENT_DATE')).fetchall()
    add_to_report("chronological", "closed opportunity with future close date", len(res), "warning", [r[0] for r in res[:5]])
    
    res = db.execute(text("""
        SELECT "Id" FROM opportunity 
        WHERE ("StageName" IN ('Closed Won', 'Closed Lost') AND ("IsClosed" = 'False' OR "IsClosed" = 'false'))
           OR ("StageName" = 'Closed Won' AND ("IsWon" = 'False' OR "IsWon" = 'false'))
           OR ("StageName" = 'Closed Lost' AND ("IsWon" = 'True' OR "IsWon" = 'true'))
    """)).fetchall()
    add_to_report("chronological", "stagename desync with isclosed/iswon flags", len(res), "high", [r[0] for r in res[:5]])
    
    # Relational checks
    res = db.execute(text('SELECT o."Id" FROM opportunity o LEFT JOIN contact c ON o."ContactId" = c."Id" WHERE c."Id" IS NULL AND o."ContactId" IS NOT NULL')).fetchall()
    add_to_report("relational", "opportunity.contactid missing in contact", len(res), "high", [r[0] for r in res[:5]])
    
    res = db.execute(text('SELECT o."Id" FROM opportunity o LEFT JOIN account a ON o."AccountId" = a."Id" WHERE a."Id" IS NULL AND o."AccountId" IS NOT NULL')).fetchall()
    add_to_report("relational", "opportunity.accountid missing in account", len(res), "high", [r[0] for r in res[:5]])
    
    res = db.execute(text('SELECT cr.consent_id FROM consent_register cr LEFT JOIN contact c ON cr.contact_id = c."Id" WHERE c."Id" IS NULL')).fetchall()
    add_to_report("relational", "consent_register.contact_id missing in contact", len(res), "high", [r[0] for r in res[:5]])

    total_opps = db.execute(text('SELECT COUNT(*) FROM opportunity WHERE "ContactId" IS NOT NULL AND "AccountId" IS NOT NULL')).scalar() or 1
    res = db.execute(text("""
        SELECT o."Id" 
        FROM opportunity o 
        JOIN contact c ON o."ContactId" = c."Id" 
        WHERE o."AccountId" != c."AccountId"
    """)).fetchall()
    rate = round(len(res) / total_opps * 100, 2)
    if len(res) > 0:
        add_to_report("relational", f"contact.accountid != opp.accountid ({rate}% rate)", len(res), "warning", [r[0] for r in res[:5]])
    
    # State/logic checks
    res = db.execute(text("""
        SELECT c."Id" FROM contact c 
        LEFT JOIN opportunity o ON c."AccountId" = o."AccountId" 
        WHERE c.lead_stage__c = 'Opportunity' AND o."Id" IS NULL
    """)).fetchall()
    add_to_report("state_logic", "Ghost Deal (lead_stage=Opportunity but no opps)", len(res), "high", [r[0] for r in res[:5]])
    
    res = db.execute(text("""
        SELECT c."Id" FROM contact c 
        LEFT JOIN opportunity o ON c."AccountId" = o."AccountId" 
        WHERE c.lead_stage__c = 'Customer' AND o."Id" IS NULL
    """)).fetchall()
    add_to_report("state_logic", "Phantom Customer (No opps at all)", len(res), "warning", [r[0] for r in res[:5]])

    res = db.execute(text("""
        SELECT c."Id" FROM contact c 
        JOIN opportunity o ON c."AccountId" = o."AccountId" 
        WHERE c.lead_stage__c = 'Customer' 
        GROUP BY c."Id" 
        HAVING SUM(CASE WHEN ("IsClosed"='True' OR "IsClosed"='true') AND ("IsWon"='True' OR "IsWon"='true') THEN 1 ELSE 0 END) = 0
    """)).fetchall()
    add_to_report("state_logic", "Phantom Customer (Opps exist but none won)", len(res), "high", [r[0] for r in res[:5]])

    res = db.execute(text("""
        SELECT c."Id" FROM contact c
        JOIN opportunity o ON c."AccountId" = o."AccountId"
        WHERE c.lead_stage__c IN ('Open','MQL','SQL') AND ("IsClosed" = 'False' OR "IsClosed" = 'false')
    """)).fetchall()
    add_to_report("state_logic", "Lazy Rep (Lead open but active opp exists)", len(res), "warning", [r[0] for r in res[:5]])
    
    res = db.execute(text("""
        SELECT "Id" FROM opportunity
        WHERE CAST(NULLIF("Probability", '') AS INT) > 0 AND CAST(NULLIF("Probability", '') AS INT) < 100 
          AND ("StageName" IN ('Closed Won', 'Closed Lost') OR ("IsClosed" = 'True' OR "IsClosed" = 'true'))
    """)).fetchall()
    add_to_report("state_logic", "Pipeline desync (Prob > 0 and < 100 but closed)", len(res), "warning", [r[0] for r in res[:5]])
    
    # Format/business logic
    res = db.execute(text('SELECT created_at FROM visitoractivity WHERE created_at IS NOT NULL')).fetchall()
    if res:
        dates = pd.Series([r[0] for r in res])
        formats = dates.apply(lambda x: 'ISO/DB' if '-' in x else ('Slash' if '/' in x else 'Text/Other')).value_counts()
        if len(formats) > 1:
            add_to_report("format", f"Multiple date formats in visitoractivity: {formats.to_dict()}", len(dates), "warning")

    res = db.execute(text("SELECT owner_id FROM sdr_roster WHERE CAST(current_capacity AS FLOAT) > CAST(max_capacity AS FLOAT)")).fetchall()
    add_to_report("format", "sdr_roster current_capacity > max_capacity", len(res), "high", [r[0] for r in res[:5]])

    res = db.execute(text("""
        SELECT s.owner_id FROM sdr_roster s
        WHERE (s.active = 'false' OR s.active = 'False') AND (
            s.owner_id IN (SELECT primary_owner_id FROM territories) OR
            s.owner_id IN (SELECT owner_id FROM routing_rules WHERE active = 'true' OR active = 'True')
        )
    """)).fetchall()
    add_to_report("format", "Inactive SDR still referenced in active rules or territories", len(res), "high", [r[0] for r in res[:5]])

    db.commit()
    return report
