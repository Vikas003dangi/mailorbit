"""add paused_reason to batches

Revision ID: f9f8af44f7ee
Revises: b35f520d7aec
Create Date: 2026-10-28 17:47:00.814132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9f8af44f7ee'
down_revision: Union[str, Sequence[str], None] = 'b35f520d7aec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("batches", sa.Column("paused_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("batches", "paused_reason")
