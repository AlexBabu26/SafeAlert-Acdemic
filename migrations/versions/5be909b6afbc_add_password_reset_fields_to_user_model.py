"""Add password reset fields to user model

Revision ID: 5be909b6afbc
Revises: a1b2c3d4e5f6
Create Date: 2026-01-25 10:39:29.162220

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5be909b6afbc'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add password reset fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reset_token', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('reset_token_expiry', sa.DateTime(), nullable=True))


def downgrade():
    # Remove password reset fields from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('reset_token_expiry')
        batch_op.drop_column('reset_token')
