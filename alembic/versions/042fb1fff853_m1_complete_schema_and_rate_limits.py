"""m1_complete_schema_and_rate_limits

Revision ID: 042fb1fff853
Revises: c52984b75fa5
Create Date: 2026-10-30 09:48:20.054746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import packages.shared.schema
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '042fb1fff853'
down_revision: Union[str, Sequence[str], None] = 'c52984b75fa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create email_otps table
    op.create_table('email_otps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('otp_hash', sa.String(length=64), nullable=False),
        sa.Column('purpose', sa.String(length=50), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_otps_email'), 'email_otps', ['email'], unique=False)
    op.create_index(op.f('ix_email_otps_expires_at'), 'email_otps', ['expires_at'], unique=False)
    op.create_index(op.f('ix_email_otps_otp_hash'), 'email_otps', ['otp_hash'], unique=False)
    op.create_index(op.f('ix_email_otps_purpose'), 'email_otps', ['purpose'], unique=False)

    # 2. Create rate_limits table (database-backed rate limiting & lockouts)
    op.create_table('rate_limits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rate_limits_key'), 'rate_limits', ['key'], unique=True)

    # 3. Create bootstrap_records table
    op.create_table('bootstrap_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bootstrap_records_token_hash'), 'bootstrap_records', ['token_hash'], unique=True)

    # 4. Create contact_replacements table
    op.create_table('contact_replacements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('purpose_id', sa.UUID(), nullable=True),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('original_contact_id', sa.UUID(), nullable=True),
        sa.Column('original_email', sa.String(length=255), nullable=False),
        sa.Column('replaced_by_contact_id', sa.UUID(), nullable=True),
        sa.Column('replaced_by_email', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['original_contact_id'], ['contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['purpose_id'], ['purposes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['replaced_by_contact_id'], ['contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contact_replacements_batch_id'), 'contact_replacements', ['batch_id'], unique=False)
    op.create_index(op.f('ix_contact_replacements_purpose_id'), 'contact_replacements', ['purpose_id'], unique=False)
    op.create_index(op.f('ix_contact_replacements_user_id'), 'contact_replacements', ['user_id'], unique=False)

    # 5. Batches index on last_run_date
    op.create_index(op.f('ix_batches_last_run_date'), 'batches', ['last_run_date'], unique=False)

    # 6. Contacts additions
    op.add_column('contacts', sa.Column('is_not_working', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('contacts', sa.Column('sequence_position', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_contacts_is_not_working'), 'contacts', ['is_not_working'], unique=False)

    # 7. Purposes additions
    op.add_column('purposes', sa.Column('daily_limit', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('purposes', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('purposes', sa.Column('stop_date', sa.Date(), nullable=True))
    op.add_column('purposes', sa.Column('skip_dates', packages.shared.schema.SafeJSON(), nullable=False, server_default='[]'))
    op.add_column('purposes', sa.Column('is_repeating', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('purposes', sa.Column('cooldown_days', sa.Integer(), nullable=False, server_default='7'))

    # 8. Users additions
    op.add_column('users', sa.Column('sender_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'token_version')
    op.drop_column('users', 'sender_name')
    op.drop_column('purposes', 'cooldown_days')
    op.drop_column('purposes', 'is_repeating')
    op.drop_column('purposes', 'skip_dates')
    op.drop_column('purposes', 'stop_date')
    op.drop_column('purposes', 'start_date')
    op.drop_column('purposes', 'daily_limit')
    op.drop_index(op.f('ix_contacts_is_not_working'), table_name='contacts')
    op.drop_column('contacts', 'sequence_position')
    op.drop_column('contacts', 'is_not_working')
    op.drop_index(op.f('ix_batches_last_run_date'), table_name='batches')
    op.drop_index(op.f('ix_contact_replacements_user_id'), table_name='contact_replacements')
    op.drop_index(op.f('ix_contact_replacements_purpose_id'), table_name='contact_replacements')
    op.drop_index(op.f('ix_contact_replacements_batch_id'), table_name='contact_replacements')
    op.drop_table('contact_replacements')
    op.drop_index(op.f('ix_bootstrap_records_token_hash'), table_name='bootstrap_records')
    op.drop_table('bootstrap_records')
    op.drop_index(op.f('ix_rate_limits_key'), table_name='rate_limits')
    op.drop_table('rate_limits')
    op.drop_index(op.f('ix_email_otps_purpose'), table_name='email_otps')
    op.drop_index(op.f('ix_email_otps_otp_hash'), table_name='email_otps')
    op.drop_index(op.f('ix_email_otps_expires_at'), table_name='email_otps')
    op.drop_index(op.f('ix_email_otps_email'), table_name='email_otps')
    op.drop_table('email_otps')
