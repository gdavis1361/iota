"""fix user role enum

Revision ID: 20240214_merge_heads
Revises: initial_migration
Create Date: 2025-02-16 20:10:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240214_merge_heads'
down_revision = 'initial_migration'
branch_labels = None
depends_on = None

def upgrade():
    # Create the enum type
    op.execute("CREATE TYPE userrole AS ENUM ('ADMIN', 'USER')")
    
    # Update existing values to uppercase
    op.execute("UPDATE users SET role = upper(role)")
    
    # Convert the column type
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
    
    # Set the default value
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'USER'::userrole")

def downgrade():
    # Convert back to varchar
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE varchar USING role::varchar")
    op.execute("DROP TYPE userrole")
