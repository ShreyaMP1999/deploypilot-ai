from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.agents.service import AgentService
from backend.auth import Principal
from backend.db.models import Action, Record, Run, User
from backend.schemas import RequestInput
from backend.workflows.service import decide_approval, start


def test_postgres_concurrent_refunds_cannot_exceed_balance(db, monkeypatch):
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Real row-lock concurrency requires PostgreSQL")
    pilot = db.scalar(select(User).where(User.username == "pilot"))
    principal = Principal(pilot.id, "northstar", "manager")
    barrier = Barrier(2)
    original = AgentService.recommend

    def synchronized(self, *args):
        result = original(self, *args)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(AgentService, "recommend", synchronized)

    def work(_):
        with Session(db.bind, expire_on_commit=False) as session:
            run = start(
                session,
                principal,
                RequestInput(text="Please refund $60.", record_id="ORD-1002", amount_cents=6000),
                str(uuid4()),
            )
            session.commit()
            return run.state

    with ThreadPoolExecutor(max_workers=2) as pool:
        states = list(pool.map(work, range(2)))
    db.expire_all()
    assert states.count("completed") == 1
    assert db.get(Record, ("northstar", "ORD-1002")).refunded_cents == 6000
    assert db.scalar(select(func.count()).select_from(Action)) == 1


def test_postgres_concurrent_approvals_execute_once(db):
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Real row-lock concurrency requires PostgreSQL")
    pilot = db.scalar(select(User).where(User.username == "pilot"))
    principal = Principal(pilot.id, "northstar", "manager")
    run = start(
        db,
        principal,
        RequestInput(text="Please refund $149.", record_id="ORD-1001", amount_cents=14900),
        str(uuid4()),
    )
    db.commit()
    barrier = Barrier(2)

    def work(_):
        with Session(db.bind, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            try:
                result = decide_approval(session, principal, run.id, "approve", "Concurrent test")
                session.commit()
                return result.state
            except HTTPException as exc:
                session.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(work, range(2)))
    db.expire_all()
    assert sorted(map(str, outcomes)) == ["409", "completed"]
    assert db.scalar(select(func.count()).select_from(Action)) == 1
    assert db.get(Run, run.id).state == "completed"
