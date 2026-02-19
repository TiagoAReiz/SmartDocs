"""add_chat_threads

Revision ID: e4a2b3c4d5e6
Revises: b3f1a9c2d4e5
Create Date: 2026-02-18 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4a2b3c4d5e6"
down_revision: Union[str, None] = "b3f1a9c2d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create chat_threads table
    op.create_table(
        "chat_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Add thread_id to chat_messages
    op.add_column("chat_messages", sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_chat_messages_thread_id"), "chat_messages", ["thread_id"], unique=False)
    op.create_foreign_key("fk_chat_messages_thread_id", "chat_messages", "chat_threads", ["thread_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_chat_messages_thread_id", "chat_messages", type_="foreignkey")
    op.drop_index(op.f("ix_chat_messages_thread_id"), table_name="chat_messages")
    op.drop_column("chat_messages", "thread_id")
    op.drop_table("chat_threads")
