"""m1_system_mail_logs_and_abuse_controls

Revision ID: 3df3d63f3b76
Revises: 042fb1fff853
Create Date: 2026-10-30 12:07:36.298196

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3df3d63f3b76'
down_revision: Union[str, Sequence[str], None] = '042fb1fff853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add system_mail_logs table."""
    op.create_table(
        'system_mail_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), server_default='LOW', nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('relay_reported_remaining', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_system_mail_logs_created_at'), 'system_mail_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_system_mail_logs_event_type'), 'system_mail_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_system_mail_logs_recipient'), 'system_mail_logs', ['recipient'], unique=False)
    op.create_index(op.f('ix_system_mail_logs_status'), 'system_mail_logs', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_mail_logs_status'), table_name='system_mail_logs')
    op.drop_index(op.f('ix_system_mail_logs_recipient'), table_name='system_mail_logs')
    op.drop_index(op.f('ix_system_mail_logs_event_type'), table_name='system_mail_logs')
    op.drop_index(op.f('ix_system_mail_logs_created_at'), table_name='system_mail_logs')
    op.drop_table('system_mail_logs')
