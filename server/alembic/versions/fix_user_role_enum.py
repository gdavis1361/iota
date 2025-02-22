"""Fix user role enum.

Revision ID: fix_user_role_enum
Revises: create_user_table
Create Date: 2024-02-22 10:31:21.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_user_role_enum"
down_revision = "create_user_table"
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema."""
    # Update the user_role enum type
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'user', 'guest')")
    op.execute(
        ("ALTER TABLE users ALTER COLUMN role TYPE user_role USING " "role::text::user_role")
    )
    op.execute("DROP TYPE user_role_old")


def downgrade():
    """Downgrade database schema."""
    # Revert the user_role enum type
    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'user')")
    op.execute(
        (
            "ALTER TABLE users ALTER COLUMN role TYPE user_role USING "
            "CASE WHEN role::text = 'guest' THEN 'user'::user_role "
            "ELSE role::text::user_role END"
        )
    )
    op.execute("DROP TYPE user_role_new")
