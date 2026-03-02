"""fix audit_logs user_id type to integer

Revision ID: a12a2ee6d6dd
Revises: a53a10a9ec63
Create Date: 2026-03-02 16:23:04.775802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a12a2ee6d6dd'
down_revision: Union[str, None] = 'a53a10a9ec63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the foreign key first if it exists
    op.execute("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_user_id_fkey")
    # Alter the column type, casting existing data to null (since UUID cannot be cast to Int)
    op.execute("ALTER TABLE audit_logs ALTER COLUMN user_id TYPE integer USING NULL")
    # Recreate the foreign key
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.execute("ALTER TABLE audit_logs ALTER COLUMN user_id TYPE uuid USING NULL")
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')
