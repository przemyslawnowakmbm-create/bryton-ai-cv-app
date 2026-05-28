"""003_rls_and_tenancy

Revision ID: 003
Revises: 002
Create Date: 2026-05-28 14:00:00.000000

Adds:
- user_tenant_assignments table (multi-tenant SM/Recruiter junction)
- RLS policies on users table (tenant isolation via SET LOCAL app.current_tenant)
- RLS policies on user_tenant_assignments table
- Grants for bryton_app role on new table
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Create user_tenant_assignments table ---
    op.create_table(
        "user_tenant_assignments",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- Enable RLS on users table ---
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")

    # Tenant isolation policy on users.
    # current_setting('app.current_tenant', true) — the 'true' second argument returns
    # NULL if the GUC has never been set (instead of raising an error).
    # The NULL/empty fallback allows migrations and superuser admin operations to
    # work without tenant context. Superusers bypass RLS entirely.
    op.execute(
        """
        CREATE POLICY tenant_isolation ON users
            USING (
                tenant_id::text = current_setting('app.current_tenant', true)
                OR current_setting('app.current_tenant', true) IS NULL
                OR current_setting('app.current_tenant', true) = ''
            )
        """
    )

    # --- Enable RLS on user_tenant_assignments table ---
    op.execute("ALTER TABLE user_tenant_assignments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_tenant_assignments FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY tenant_isolation ON user_tenant_assignments
            USING (
                tenant_id::text = current_setting('app.current_tenant', true)
                OR current_setting('app.current_tenant', true) IS NULL
                OR current_setting('app.current_tenant', true) = ''
            )
        """
    )

    # --- Grant permissions to bryton_app role for the new table ---
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON user_tenant_assignments TO bryton_app"
    )


def downgrade() -> None:
    # Drop RLS policies first, then disable RLS, then drop table
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON user_tenant_assignments")
    op.execute("ALTER TABLE user_tenant_assignments DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS user_tenant_assignments")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
