"""create attachments and purpose_attachments tables

Revision ID: b35f520d7aec
Revises: 8a0f0abf9e67
Create Date: 2026-10-28 17:13:19.397229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b35f520d7aec'
down_revision: Union[str, Sequence[str], None] = '8a0f0abf9e67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=False),
        sa.Column("cloudinary_public_id", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), server_default="application/pdf", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_attachments_user_id", "attachments", ["user_id"], unique=False)

    op.create_table(
        "purpose_attachments",
        sa.Column("purpose_id", sa.UUID(as_uuid=True), sa.ForeignKey("purposes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("attachment_id", sa.UUID(as_uuid=True), sa.ForeignKey("attachments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("purpose_attachments")
    op.drop_index("ix_attachments_user_id", table_name="attachments")
    op.drop_table("attachments")
