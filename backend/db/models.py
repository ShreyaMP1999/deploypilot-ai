from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def uid():
    return str(uuid4())


def now():
    return datetime.now(UTC)


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    workflow = Column(String, nullable=False)


class Configuration(Base):
    __tablename__ = "tenant_configurations"
    tenant_id = Column(ForeignKey("tenants.id"), primary_key=True)
    integrations = Column(JSON, nullable=False)
    environment = Column(String, default="synthetic-local", nullable=False)


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("tenant_id", "version"),)
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    rules = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uid)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    user_id = Column(ForeignKey("users.id"), primary_key=True)
    tenant_id = Column(ForeignKey("tenants.id"), primary_key=True)
    role = Column(String, nullable=False)


class Record(Base):
    __tablename__ = "integration_records"
    __table_args__ = (CheckConstraint("refunded_cents >= 0"),)
    tenant_id = Column(ForeignKey("tenants.id"), primary_key=True)
    id = Column(String, primary_key=True)
    kind = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    refunded_cents = Column(Integer, nullable=False, default=0)


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    idempotency_key = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Run(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True, default=uid)
    request_id = Column(ForeignKey("requests.id"), unique=True, nullable=False)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    policy_id = Column(ForeignKey("policies.id"), nullable=False)
    state = Column(String, nullable=False, default="received", index=True)
    context = Column(JSON, nullable=False, default=dict)
    recommendation = Column(JSON, nullable=False, default=dict)
    decision = Column(JSON, nullable=False, default=dict)
    action = Column(JSON, nullable=False, default=dict)
    action_hash = Column(String, nullable=False, default="")
    model = Column(String, nullable=False, default="offline-rules")
    prompt_version = Column(String, nullable=False, default="v1")
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost = Column(Float, nullable=False, default=0)
    latency_ms = Column(Float, nullable=False, default=0)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String, primary_key=True, default=uid)
    run_id = Column(ForeignKey("agent_runs.id"), unique=True, nullable=False)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    action_hash = Column(String, nullable=False)
    policy_id = Column(ForeignKey("policies.id"), nullable=False)
    required_role = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    actor_id = Column(ForeignKey("users.id"))
    note = Column(Text)
    decided_at = Column(DateTime(timezone=True))


class Action(Base):
    __tablename__ = "executed_actions"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    run_id = Column(ForeignKey("agent_runs.id"), unique=True, nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Audit(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    run_id = Column(ForeignKey("agent_runs.id"), nullable=False, index=True)
    event = Column(String, nullable=False)
    detail = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"
    id = Column(String, primary_key=True)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    data = Column(JSON, nullable=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, index=True)
    model = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
