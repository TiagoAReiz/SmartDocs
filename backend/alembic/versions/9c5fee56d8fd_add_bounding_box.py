"""add_bounding_box

Revision ID: 9c5fee56d8fd
Revises: adc0879ff4c1
Create Date: 2026-02-15 17:35:29.590018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c5fee56d8fd"
down_revision: Union[str, None] = "adc0879ff4c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_fields", sa.Column("bounding_box", sa.JSON(), nullable=True))
    op.add_column("document_logs", sa.Column("event_type", sa.String(length=100), nullable=True))
    op.add_column("document_logs", sa.Column("message", sa.Text(), nullable=True))
    op.execute("UPDATE document_logs SET event_type = event, message = details")
    op.alter_column("document_logs", "event_type", nullable=False)
    op.drop_column("document_logs", "event")
    op.drop_column("document_logs", "details")


def downgrade() -> None:
    op.add_column(
        "document_logs",
        sa.Column("details", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "document_logs",
        sa.Column("event", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    )
    op.execute("UPDATE document_logs SET event = event_type, details = message")
    op.drop_column("document_logs", "message")
    op.drop_column("document_logs", "event_type")
    op.drop_column("document_fields", "bounding_box")
