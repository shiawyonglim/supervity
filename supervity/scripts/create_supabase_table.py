import os
from sqlalchemy import create_engine, text

# Supabase database connection string
DATABASE_URI = "postgresql://postgres:oJVlk5z0nL8CnGGD6@db.fxprndpxwhdrwmgpgasq.supabase.co:5432/postgres"

def create_supervity_table():
    print("Connecting to Supabase...")
    engine = create_engine(DATABASE_URI)
    
    with engine.begin() as conn:
        print("Creating table 'supervity_queue'...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS supervity_queue (
                id SERIAL PRIMARY KEY,
                prospect_id VARCHAR(255) NOT NULL,
                payload JSONB NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("Table 'supervity_queue' created successfully!")

if __name__ == "__main__":
    create_supervity_table()
