# app/core/schema_patch.py
"""
Idempotent additive schema patches.

`Base.metadata.create_all()` creates missing TABLES but never adds missing COLUMNS to
tables that already exist. When a model gains a column, existing databases (including
the judges' running instance and any dev volume that predates the change) would keep
the old shape and every query touching the new column would fail.

Each entry here is an additive `ADD COLUMN IF NOT EXISTS`, which is safe to run on
every boot and never destroys data. Anything beyond additive changes belongs in a
proper Alembic migration.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

# (table, column, column_definition)
ADDITIVE_COLUMNS = [
    # AI Insights: WHO the insight is for / WHAT happens if they don't act.
    # (`suggested_action` — what to do now — already existed.)
    ("insights", "owner_name", "VARCHAR(255)"),
    ("insights", "owner_role", "VARCHAR(150)"),
    ("insights", "owner_id", "VARCHAR(50)"),
    ("insights", "consequence", "TEXT"),
    # Revenue org chain: point each SDR at the Sales Agent they hand qualified
    # leads up to. `sdr_roster` is a raw CSV-seeded table, so create_all cannot
    # add this — patch it in here.
    ("sdr_roster", "sales_agent_id", "VARCHAR(50)"),
    ("sdr_roster", "max_capacity", "INTEGER"),
    ("sdr_roster", "current_capacity", "INTEGER"),
]


def apply_additive_columns(engine: Engine) -> None:
    """Add any columns that models declare but the live tables are missing."""
    for table, column, coltype in ADDITIVE_COLUMNS:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{column}" {coltype}')
                )
        except Exception as e:
            # A missing table is fine — create_all will have made it with the column
            # already present. Anything else is worth surfacing but must not block boot.
            log.warning(f"Schema patch skipped for {table}.{column}: {e}")
