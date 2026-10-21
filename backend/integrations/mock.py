"""Local adapters. All actions are database-only, synthetic side effects."""

from typing import Protocol
from sqlalchemy import select
from backend.db.models import Record, Action


class IntegrationError(Exception):
    pass


class Integration(Protocol):
    def retrieve(self, tenant_id: str, record_id: str) -> dict | None: ...
    def execute(self, run, action: dict) -> dict: ...


class MockIntegration:
    def __init__(self, db):
        self.db = db

    def retrieve(self, tenant_id, record_id):
        record = self.db.get(Record, (tenant_id, record_id))
        if record and record.data.get("tool_failure"):
            raise IntegrationError("Mock source is temporarily unavailable.")
        return {**record.data, "refunded_cents": record.refunded_cents} if record else None

    def execute(self, run, action):
        prior = self.db.scalar(select(Action).where(Action.run_id == run.id))
        if prior:
            return prior.result
        record = self.db.scalar(
            select(Record)
            .where(Record.tenant_id == run.tenant_id, Record.id == action["record_id"])
            .with_for_update()
        )
        if action["kind"] == "refund":
            if (
                not record
                or record.refunded_cents + action["amount_cents"] > record.data["total_cents"]
            ):
                raise IntegrationError("Refund balance changed; submit a new request.")
            record.refunded_cents += action["amount_cents"]
            result = {
                "simulated": True,
                "refunded_cents": action["amount_cents"],
                "payment_method": "original",
            }
        elif action["kind"] in {"draft_response", "escalate_access", "route_review"}:
            result = {
                "simulated": True,
                "ticket_status": "drafted" if action["kind"] == "draft_response" else "escalated",
                "credential_changed": False,
            }
        else:
            raise IntegrationError("Action is not permitted by this adapter.")
        self.db.add(Action(tenant_id=run.tenant_id, run_id=run.id, payload=action, result=result))
        self.db.flush()
        return result
