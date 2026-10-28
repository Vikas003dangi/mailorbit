from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from packages.shared.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sender_relays = relationship("SenderRelay", back_populates="user", cascade="all, delete-orphan")
    ai_keys = relationship("AIKey", back_populates="user", cascade="all, delete-orphan")
    purposes = relationship("Purpose", back_populates="user", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")


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
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="purposes")
    batches = relationship("Batch", back_populates="purpose", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="purpose")


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
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="batches")
    purpose = relationship("Purpose", back_populates="batches")
    contacts = relationship("Contact", back_populates="batch")


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
