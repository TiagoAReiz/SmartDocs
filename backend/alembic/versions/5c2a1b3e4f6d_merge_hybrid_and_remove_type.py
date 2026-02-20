"""merge hybrid search and remove_document_type

Revision ID: 5c2a1b3e4f6d
Revises: 3b1f9c8d2a6e, 71d928dc7852
Create Date: 2026-02-19 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c2a1b3e4f6d'
down_revision: Union[tuple[str, ...], str, None] = ('3b1f9c8d2a6e', '9fac960e2063')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
