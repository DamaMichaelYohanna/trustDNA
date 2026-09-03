"""SQLAlchemy ORM models for TrustDNA (SQLite and PostgreSQL compatible)."""
import time
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    Text,
    ForeignKey,
    Index
)
from sqlalchemy.orm import relationship
from .session import Base


class TenantDB(Base):
    __tablename__ = "tenants"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    industry = Column(String(64), default="Fintech & Payments")
    plan = Column(String(32), default="Scale")
    created_at_epoch = Column(Float, default=time.time)

    # Relationships
    api_keys = relationship("ApiKeyDB", back_populates="tenant", cascade="all, delete-orphan", lazy="joined")
    settings = relationship("TenantSettingsDB", back_populates="tenant", uselist=False, cascade="all, delete-orphan", lazy="joined")
    metrics = relationship("TenantMetricsDB", back_populates="tenant", uselist=False, cascade="all, delete-orphan", lazy="joined")
    audit_logs = relationship("DecisionAuditLogDB", back_populates="tenant", cascade="all, delete-orphan", lazy="selectin")


class ApiKeyDB(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), default="Primary Key")
    publishable_key = Column(String(128), unique=True, index=True, nullable=False)
    secret_key = Column(String(128), unique=True, index=True, nullable=False)
    environment = Column(String(32), default="sandbox")
    created_at_epoch = Column(Float, default=time.time)
    status = Column(String(32), default="active")  # "active" or "revoked"

    tenant = relationship("TenantDB", back_populates="api_keys")


class TenantSettingsDB(Base):
    __tablename__ = "tenant_settings"

    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    allow_threshold = Column(Integer, default=70)
    mfa_threshold = Column(Integer, default=40)
    block_threshold = Column(Integer, default=39)
    impossible_travel_enabled = Column(Boolean, default=True)
    bot_cadence_enabled = Column(Boolean, default=True)
    touch_biometrics_enabled = Column(Boolean, default=True)
    velocity_spike_enabled = Column(Boolean, default=True)
    webhook_url = Column(String(256), nullable=True)
    webhook_secret = Column(String(128), nullable=True)

    tenant = relationship("TenantDB", back_populates="settings")


class TenantMetricsDB(Base):
    __tablename__ = "tenant_metrics"

    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    total_evaluations = Column(Integer, default=0)
    allow_count = Column(Integer, default=0)
    challenge_count = Column(Integer, default=0)
    block_count = Column(Integer, default=0)
    total_latency_ms = Column(Float, default=0.0)

    tenant = relationship("TenantDB", back_populates="metrics")


class DecisionAuditLogDB(Base):
    __tablename__ = "decision_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(128), index=True)
    trust_score = Column(Float, nullable=False)
    decision = Column(String(32), nullable=False)
    latency_ms = Column(Float, default=0.0)
    reasons_json = Column(Text, default="[]")  # JSON string of reason tags
    amount = Column(Float, default=0.0)
    currency = Column(String(16), default="USD")
    timestamp = Column(Float, default=time.time, index=True)

    tenant = relationship("TenantDB", back_populates="audit_logs")


Index("ix_audit_tenant_time", DecisionAuditLogDB.tenant_id, DecisionAuditLogDB.timestamp.desc())
