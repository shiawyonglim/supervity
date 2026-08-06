import pandas as pd
import os
import re

data_dir = r"c:\supervity\supervity\data"

files = {
    "VisitorActivity": "VisitorActivity.csv",
    "Contact": "Contact.csv",
    "Account": "Account.csv",
    "Opportunity": "Opportunity.csv",
    "ICP_Scoring_Config": "ICP_Scoring_Config.csv",
    "Enrichment_Data": "Enrichment_Data.csv",
    "Territories": "Territories.csv",
    "Routing_Rules": "Routing_Rules.csv",
    "SDR_Roster": "SDR_Roster.csv",
    "Consent_Register": "Consent_Register.csv",
    "Sequences": "Sequences.csv",
    "Buying_Group": "Buying_Group.csv",
}

dfs = {}
for name, file in files.items():
    try:
        # Load all as strings initially to check formats without pandas auto-converting, except some known numeric columns
        dfs[name] = pd.read_csv(os.path.join(data_dir, file), dtype=str)
    except Exception as e:
        print(f"Failed to load {name}: {e}")

print("==================================================")
print("COMPREHENSIVE DATA QUALITY REPORT")
print("==================================================\n")

# 1. EMPTY CELLS (Missing Values)
print("--- 1. MISSING VALUES (EMPTY CELLS) ---")
for name, df in dfs.items():
    missing = df.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        print(f"[{name}] Missing values found:")
        for col, count in missing.items():
            print(f"   - {col}: {count} empty cells ({count/len(df)*100:.1f}%)")
print()

# 2. DUPLICATE PRIMARY KEYS & EXACT ROW DUPLICATES
print("--- 2. DUPLICATES ---")
pk_map = {
    "Contact": "Id",
    "Account": "Id",
    "Opportunity": "Id",
    "Enrichment_Data": "enrichment_id",
    "Territories": "territory_id",
    "Routing_Rules": "rule_id",
    "SDR_Roster": "owner_id",
    "Consent_Register": "consent_id",
    "Sequences": "sequence_id"
}

for name, df in dfs.items():
    # Exact row duplicates
    exact_dupes = df.duplicated().sum()
    if exact_dupes > 0:
        print(f"[{name}] {exact_dupes} exact duplicate rows found.")
    
    # Primary key duplicates
    if name in pk_map and pk_map[name] in df.columns:
        pk_col = pk_map[name]
        pk_dupes = df.duplicated(subset=[pk_col]).sum()
        if pk_dupes > 0:
            print(f"[{name}] [CRITICAL] {pk_dupes} duplicate Primary Keys ({pk_col}) found.")
            
    # Business logic duplicates (e.g. Contact emails)
    if name == 'Contact' and 'email' in df.columns:
        email_dupes = df.duplicated(subset=['email']).sum()
        if email_dupes > 0:
            print(f"[Contact] {email_dupes} duplicate emails found.")
print()

# 3. DATA FORMATTING & INCONSISTENCIES
print("--- 3. FORMAT INCONSISTENCIES ---")

# Email Format Check
if 'Contact' in dfs and 'email' in dfs['Contact'].columns:
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    invalid_emails = dfs['Contact'][~dfs['Contact']['email'].astype(str).str.match(email_regex, na=False)]
    if not invalid_emails.empty:
        print(f"[Contact] {len(invalid_emails)} invalid email formats found.")

# Date Format Check
date_columns = {
    'VisitorActivity': ['created_at'],
    'Opportunity': ['CloseDate', 'CreatedDate'],
    'Enrichment_Data': ['last_verified'],
    'Consent_Register': ['captured_at', 'expires_at'],
    'Buying_Group': ['added_at']
}

for name, cols in date_columns.items():
    if name in dfs:
        for col in cols:
            if col in dfs[name].columns:
                non_nulls = dfs[name][col].dropna()
                if not non_nulls.empty:
                    # Try to parse with standard ISO format
                    parsed = pd.to_datetime(non_nulls, errors='coerce', format='mixed')
                    invalid_dates = parsed.isna().sum()
                    
                    # Let's also check for distinct formats manually (heuristic)
                    formats = non_nulls.apply(lambda x: 'ISO/DB' if '-' in x else ('Slash' if '/' in x else 'Text/Other')).value_counts()
                    
                    if invalid_dates > 0:
                        print(f"[{name}.{col}] {invalid_dates} unparseable/invalid dates found.")
                    if len(formats) > 1:
                        print(f"[{name}.{col}] Inconsistent date formats detected:")
                        for fmt, count in formats.items():
                            print(f"   - {fmt}: {count} rows")

print()

# 4. BUSINESS LOGIC & ANOMALIES
print("--- 4. BUSINESS LOGIC ANOMALIES ---")
# Check for negative or non-numeric values where numbers are expected
if 'Opportunity' in dfs and 'Amount' in dfs['Opportunity'].columns:
    amounts = pd.to_numeric(dfs['Opportunity']['Amount'], errors='coerce')
    invalid_amounts = amounts.isna().sum() - dfs['Opportunity']['Amount'].isna().sum()
    neg_amounts = (amounts < 0).sum()
    if invalid_amounts > 0:
         print(f"[Opportunity.Amount] {invalid_amounts} non-numeric amounts.")
    if neg_amounts > 0:
         print(f"[Opportunity.Amount] {neg_amounts} negative amounts.")

if 'SDR_Roster' in dfs and 'current_capacity' in dfs['SDR_Roster'].columns and 'max_capacity' in dfs['SDR_Roster'].columns:
    curr = pd.to_numeric(dfs['SDR_Roster']['current_capacity'], errors='coerce')
    max_cap = pd.to_numeric(dfs['SDR_Roster']['max_capacity'], errors='coerce')
    over_cap = (curr > max_cap).sum()
    if over_cap > 0:
        print(f"[SDR_Roster] {over_cap} SDRs are over their max capacity!")

print()

# 5. FOREIGN KEY RELATIONSHIPS
print("--- 5. FOREIGN KEY MISMATCHES (ORPHANS) ---")
contact_ids = set(dfs['Contact']['Id'].dropna()) if 'Contact' in dfs and 'Id' in dfs['Contact'].columns else set()
account_ids = set(dfs['Account']['Id'].dropna()) if 'Account' in dfs and 'Id' in dfs['Account'].columns else set()
sdr_ids = set(dfs['SDR_Roster']['owner_id'].dropna()) if 'SDR_Roster' in dfs and 'owner_id' in dfs['SDR_Roster'].columns else set()

errors_found = 0

def check_fk(df_name, fk_col, parent_name, parent_keys):
    global errors_found
    if df_name in dfs and fk_col in dfs[df_name].columns:
        fk_values = set(dfs[df_name][fk_col].dropna())
        dangling = fk_values - parent_keys
        if dangling:
            print(f"[ERROR] {df_name}.{fk_col} has {len(dangling)} values not found in {parent_name} (Examples: {list(dangling)[:3]})")
            errors_found += 1

check_fk('VisitorActivity', 'prospect_id', 'Contact', contact_ids)
check_fk('Contact', 'AccountId', 'Account', account_ids)
check_fk('Opportunity', 'AccountId', 'Account', account_ids)
check_fk('Opportunity', 'ContactId', 'Contact', contact_ids)
check_fk('Enrichment_Data', 'matched_account_id', 'Account', account_ids)
check_fk('Buying_Group', 'account_id', 'Account', account_ids)
check_fk('Buying_Group', 'contact_id', 'Contact', contact_ids)
check_fk('Consent_Register', 'contact_id', 'Contact', contact_ids)
check_fk('Routing_Rules', 'owner_id', 'SDR_Roster', sdr_ids)
check_fk('Territories', 'primary_owner_id', 'SDR_Roster', sdr_ids)

if errors_found == 0:
    print("No foreign key mismatches found.")

print("\n==================================================")
print("ANALYSIS COMPLETE")
print("==================================================")
