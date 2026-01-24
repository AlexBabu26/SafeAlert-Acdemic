"""Rename is_dispatcher to is_department in users table

Revision ID: a1b2c3d4e5f6
Revises: 4ad2afe6448c
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '4ad2afe6448c'
branch_labels = None
depends_on = None


def upgrade():
    """Rename is_dispatcher column to is_department"""
    # For SQLite, we need to use batch operations
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('is_dispatcher', new_column_name='is_department')


def downgrade():
    """Revert: rename is_department back to is_dispatcher"""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('is_department', new_column_name='is_dispatcher')

