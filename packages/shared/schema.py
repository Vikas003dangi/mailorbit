from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    CHAR,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from packages.shared.db import Base


class SafeUUID(TypeDecorator):
    """Platform-independent UUID. Native PostgreSQL UUID in prod; CHAR(36) in SQLite."""
    impl = CHAR(36)
    cache_ok = True

    def __init__(self, as_uuid: bool = True):
        super().__init__()
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return value


class SafeJSON(TypeDecorator):
    """Platform-independent JSON. Native JSONB in PostgreSQL; standard JSON in SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
            return dialect.type_descriptor(PG_JSONB)
        return dialect.type_descriptor(JSON)


# Backward-compatible drop-in aliases
UUID = SafeUUID
JSONB = SafeJSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    verification_token_hash = Column(String(255), nullable=True)
    verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    reset_token_hash = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    sender_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sender_relays = relationship("SenderRelay", back_populates="user", cascade="all, delete-orphan")
    ai_keys = relationship("AIKey", back_populates="user", cascade="all, delete-orphan")
    purposes = relationship("Purpose", back_populates="user", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="user", cascade="all, delete-orphan")
    do_not_contact_records = relationship("DoNotContact", back_populates="user", cascade="all, delete-orphan")
    replacements = relationship("ContactReplacement", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    links = Column(JSONB, default=dict, nullable=False)  # github, linkedin, portfolio, etc.
    skills = Column(JSONB, default=list, nullable=False)  # list of skill strings
    experience = Column(JSONB, default=list, nullable=False)  # list of experience dicts
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="profile")


class SenderRelay(Base):
    __tablename__ = "sender_relays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    provider = Column(String(50), default="google_apps_script", nullable=False)
    script_url = Column(Text, nullable=False)
    auth_token_ciphertext = Column(Text, nullable=False)  # Encrypted with AES-256-GCM
    daily_cap = Column(Integer, default=30, nullable=False)
    remaining_quota = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="PENDING_TEST", nullable=False)  # ACTIVE, PENDING_TEST, QUOTA_EXCEEDED, ERROR
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="sender_relays")


class AIKey(Base):
    __tablename__ = "ai_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), default="gemini", nullable=False)
    api_key_ciphertext = Column(Text, nullable=False)  # Encrypted with AES-256-GCM
    model = Column(String(100), default="gemini-2.5-flash", nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, INVALID, REVOKED
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="ai_keys")


class Purpose(Base):
    """
    General Outreach Campaign Purpose (e.g. Job Application, Referral Request,
    Freelance Pitch, Follow-up, Custom). Each purpose maintains its own templates,
    prompts, and auto-batching parameters.
    """
    __tablename__ = "purposes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    default_subject_template = Column(String(255), nullable=True)
    default_body_template = Column(Text, nullable=True)
    daily_limit = Column(Integer, default=30, nullable=False)
    start_date = Column(Date, nullable=True)
    stop_date = Column(Date, nullable=True)
    skip_dates = Column(JSONB, default=list, nullable=False)
    is_repeating = Column(Boolean, default=False, nullable=False)
    cooldown_days = Column(Integer, default=7, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="purposes")
    batches = relationship("Batch", back_populates="purpose", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="purpose")
    attachments = relationship("Attachment", secondary="purpose_attachments", back_populates="purposes")


class Batch(Base):
    """
    Named batch auto-created from scheduling rules (e.g. N per day, at time T on days D).
    Allows user to rename, adjust size, pause, or view contacts.
    """
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose_id = Column(UUID(as_uuid=True), ForeignKey("purposes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    size = Column(Integer, default=30, nullable=False)
    position = Column(Integer, default=1, nullable=False)
    scheduled_time = Column(String(20), default="10:00", nullable=True)  # e.g. "10:00"
    scheduled_days = Column(JSONB, default=lambda: ["mon", "tue", "wed", "thu", "fri"], nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, ACTIVE, COMPLETED, PAUSED
    paused_reason = Column(Text, nullable=True)
    last_run_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="batches")
    purpose = relationship("Purpose", back_populates="batches")
    contacts = relationship("Contact", back_populates="batch")


purpose_attachments = Table(
    "purpose_attachments",
    Base.metadata,
    Column("purpose_id", UUID(as_uuid=True), ForeignKey("purposes.id", ondelete="CASCADE"), primary_key=True),
    Column("attachment_id", UUID(as_uuid=True), ForeignKey("attachments.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class Attachment(Base):
    """
    Document library item stored in Cloudinary (e.g. Resume, Portfolio, Proposal).
    Delivered with signed/authenticated URLs and linkable to multiple campaign purposes.
    """
    __tablename__ = "attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_url = Column(String(1024), nullable=False)
    cloudinary_public_id = Column(String(255), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(100), default="application/pdf", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="attachments")
    purposes = relationship("Purpose", secondary=purpose_attachments, back_populates="attachments")


class Contact(Base):
    """
    Lead contact representing a recipient of cold outreach.
    Supports deduplication, immediate failure detection, and inactive listing.
    """
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose_id = Column(UUID(as_uuid=True), ForeignKey("purposes.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    role = Column(String(255), nullable=True)
    custom_pitch = Column(JSONB, default=dict, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, QUEUED, SENT, BOUNCED, INVALID_DOMAIN, INACTIVE, UNSUBSCRIBED
    status_reason = Column(Text, nullable=True)
    is_not_working = Column(Boolean, default=False, nullable=False, index=True)
    sequence_position = Column(Integer, default=0, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="contacts")
    purpose = relationship("Purpose", back_populates="contacts")
    batch = relationship("Batch", back_populates="contacts")

    __table_args__ = (
        UniqueConstraint("user_id", "email", name="uq_user_contact_email"),
        Index("ix_contacts_user_status", "user_id", "status"),
        Index("ix_contacts_user_purpose_status", "user_id", "purpose_id", "status"),
    )


class DoNotContact(Base):
    """
    Opt-out registry protecting recipients from future outreach.
    Checked before every send.
    """
    __tablename__ = "do_not_contact"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    reason = Column(String(255), default="Unsubscribed", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="do_not_contact_records")

    __table_args__ = (
        UniqueConstraint("user_id", "email", name="uq_user_dnc_email"),
        Index("ix_dnc_user_email", "user_id", "email"),
    )


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, default=dict, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    run_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    lease_id = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class BootstrapRecord(Base):
    __tablename__ = "bootstrap_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consumed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    ip_address = Column(String(45), nullable=True)


class ContactReplacement(Base):
    """
    Audit log of automatically or manually quarantined dead/bounced leads
    and the replacement lead pulled in to fulfill the daily batch quota.
    """
    __tablename__ = "contact_replacements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose_id = Column(UUID(as_uuid=True), ForeignKey("purposes.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)
    original_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    original_email = Column(String(255), nullable=False)
    replaced_by_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    replaced_by_email = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="replacements")


class EmailOTP(Base):
    """
    Cryptographically secure single-use OTP codes for email verification,
    password reset, password update, and account deletion.
    """
    __tablename__ = "email_otps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False, index=True)
    purpose = Column(String(50), nullable=False, index=True)  # signup, forgot_password, change_password, delete_account
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


