"""Initial migration - create Graph Registry tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type if not exists (handle case where it was already created)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'graphstatusenum') THEN
                CREATE TYPE graphstatusenum AS ENUM ('DRAFT', 'PUBLISHED', 'ARCHIVED');
            END IF;
        END $$
    """)
    
    # Create intents table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS intents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) UNIQUE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    # Create graphs table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS graphs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            intent_id UUID NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
            version VARCHAR(50) NOT NULL,
            graph_json JSONB NOT NULL,
            status graphstatusenum NOT NULL DEFAULT 'DRAFT',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create indexes if not exists
    op.execute("CREATE INDEX IF NOT EXISTS idx_graphs_intent_id ON graphs(intent_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_graphs_intent_version ON graphs(intent_id, version)")

    # Create graph_audit_log table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS graph_audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            graph_id UUID NOT NULL REFERENCES graphs(id) ON DELETE CASCADE,
            action VARCHAR(100) NOT NULL,
            status_before graphstatusenum,
            status_after graphstatusenum,
            performed_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_graph_audit_log_graph_id ON graph_audit_log(graph_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_graph_audit_log_performed_at ON graph_audit_log(performed_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_graph_audit_log_performed_at")
    op.execute("DROP INDEX IF EXISTS idx_graph_audit_log_graph_id")
    op.execute("DROP TABLE IF EXISTS graph_audit_log")
    op.execute("DROP INDEX IF EXISTS idx_graphs_intent_version")
    op.execute("DROP INDEX IF EXISTS idx_graphs_intent_id")
    op.execute("DROP TABLE IF EXISTS graphs")
    op.execute("DROP TABLE IF EXISTS intents")
    op.execute("DROP TYPE IF EXISTS graphstatusenum")