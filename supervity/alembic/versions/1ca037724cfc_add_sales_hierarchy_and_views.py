"""add_sales_hierarchy_and_views

Revision ID: 1ca037724cfc
Revises: f4bf9d520087
Create Date: 2026-08-08 19:16:21.983995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ca037724cfc'
down_revision: Union[str, None] = 'f4bf9d520087'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tables
    op.create_table(
        'sales_managers',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('max_capacity', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'sales_agents',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('max_capacity', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('sales_manager_id', sa.String(length=50), sa.ForeignKey('sales_managers.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'cros',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('max_capacity', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Add column to sdr_roster
    op.add_column('sdr_roster', sa.Column('sales_agent_id', sa.String(length=50), sa.ForeignKey('sales_agents.id'), nullable=True))

    # 3. Create views
    op.execute("""
        CREATE OR REPLACE VIEW sdr_workload AS
        SELECT c."OwnerId" AS owner_id, COUNT(*) AS current_capacity
        FROM contact c
        WHERE c."Lead_Stage__c" = 'Open'
        GROUP BY c."OwnerId";
    """)

    op.execute("""
        CREATE OR REPLACE VIEW sales_agent_workload AS
        SELECT sr.sales_agent_id, COUNT(*) AS current_capacity
        FROM contact c
        JOIN sdr_roster sr ON c."OwnerId" = sr.owner_id
        WHERE c."Lead_Stage__c" IN ('Opportunity', 'MQL')
          AND sr.sales_agent_id IS NOT NULL
        GROUP BY sr.sales_agent_id;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW sales_manager_workload AS
        SELECT sa.sales_manager_id, COUNT(*) AS current_capacity
        FROM contact c
        JOIN sdr_roster sr ON c."OwnerId" = sr.owner_id
        JOIN sales_agents sa ON sr.sales_agent_id = sa.id
        WHERE c."Lead_Stage__c" = 'SQL'
          AND sa.sales_manager_id IS NOT NULL
        GROUP BY sa.sales_manager_id;
    """)
    # Note: CRO workload left uncomputed as per product decision

    # 4. Insert seed data
    op.execute("INSERT INTO sales_managers (id, name, email, max_capacity, active) VALUES ('SM001', 'Kim Hopester', 'ykazugaya@gmail.com', 90, true);")
    op.execute("INSERT INTO sales_agents (id, name, email, max_capacity, active, sales_manager_id) VALUES ('SA001', 'Khee En', 'kheeenteo13@gmail.com', 80, true, 'SM001');")
    op.execute("INSERT INTO sales_agents (id, name, email, max_capacity, active, sales_manager_id) VALUES ('SA002', 'Kimberly Tey', 'teykimberly@supervity.ai', 80, true, 'SM001');")
    op.execute("INSERT INTO cros (id, name, email, max_capacity, active) VALUES ('CR0001', 'Bratt Frasser', 'bratt@supervity.ai', 10, true);")
    
    # 5. Update SDR Roster Mapping
    op.execute("UPDATE sdr_roster SET sales_agent_id = 'SA001' WHERE owner_id IN ('005AE1', '005AE2', '005AE3');")
    op.execute("UPDATE sdr_roster SET sales_agent_id = 'SA002' WHERE owner_id IN ('005AE4', '005AE5');")

def downgrade() -> None:
    # 1. Revert SDR roster column
    op.drop_column('sdr_roster', 'sales_agent_id')

    # 2. Drop views
    op.execute("DROP VIEW IF EXISTS sales_manager_workload;")
    op.execute("DROP VIEW IF EXISTS sales_agent_workload;")
    op.execute("DROP VIEW IF EXISTS sdr_workload;")

    # 3. Drop tables
    op.drop_table('cros')
    op.drop_table('sales_agents')
    op.drop_table('sales_managers')
