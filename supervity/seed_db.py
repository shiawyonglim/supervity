import os
import pandas as pd
from sqlalchemy import create_engine

# Automatically find the exact folder where this seed_db.py script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database URL for host access (connecting to localhost:5432)
DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/app_db"
)

# All CSV files from the Round 2 data pack
CSV_FILES = [
    "Account.csv",
    "Buying_Group.csv",
    "Consent_Register.csv",
    "Contact.csv",
    "Enrichment_Data.csv",
    "Field_Dictionary.csv",
    "ICP_Scoring_Config.csv",
    "Opportunity.csv",
    "Routing_Rules.csv",
    "SDR_Roster.csv",
    "Sequences.csv",
    "Territories.csv",
    "VisitorActivity.csv",
]

def main():
    print(f"Connecting to database at {DB_URL}...")
    engine = create_engine(DB_URL)

    for file_name in CSV_FILES:
        file_path = os.path.join(BASE_DIR, file_name)

        if not os.path.exists(file_path):
            print(f"⚠️  Skipping {file_name}: File not found at {file_path}")
            continue

        table_name = file_name.replace(".csv", "").lower()
        print(f"Importing {file_name} -> table '{table_name}'...")
        df = pd.read_csv(file_path)

        # Upload to PostgreSQL using a managed connection block
        with engine.begin() as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            
        print(f"✅ Loaded {len(df)} rows into '{table_name}'.")

    print("\n🎉 Database seeding complete!")

if __name__ == "__main__":
    main()