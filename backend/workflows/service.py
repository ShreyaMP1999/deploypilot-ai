import hashlib
import json
import logging
from time import perf_counter

from fastapi import HTTPException
from sqlalchemy import select

from backend.agents.service import PROMPT_VERSION, AgentService
from backend.db.models import Approval, Audit, Policy, Request, Run, Tenant
from backend.integrations.mock import IntegrationError, MockIntegration
from backend.policies.engine import decide
from backend.schemas import Recommendation, RequestInput

logger = logging.getLogger("deploypilot")
TRANSITIONS = {
    "received": {"analyzing", "failed"},
    "analyzing": {"awaiting_approval", "rejected", "executing", "failed"},
    "awaiting_approval": {"approved", "rejected", "failed"},
    "approved": {"executing", "failed"},
    "executing": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
    "rejected": set(),
}


def audit(db, run, event, detail):
    db.add(Audit(tenant_id=run.tenant_id, run_id=run.id, event=event, detail=detail))
    logger.info(json.dumps({"event": event, "run_id": run.id, "tenant_id": run.tenant_id}))


def transition(db, run, state):
    if state not in TRANSITIONS[run.state]:
        raise HTTPException(409, f"Invalid state transition: {run.state} to {state}")
    previous = run.state
    run.state = state
    audit(db, run, "state_transition", {"from": previous, "to": state})


def current_policy(db, tenant_id):
    return db.scalar(
        select(Policy).where(Policy.tenant_id == tenant_id).order_by(Policy.version.desc()).limit(1)
    )


def fingerprint(action, policy_id):
    return hashlib.sha256(
        json.dumps({"action": action, "policy_id": policy_id}, sort_keys=True).encode()
    ).hexdigest()


def execute(db, run):
    transition(db, run, "executing")
    try:
        result = MockIntegration(db).execute(run, run.action)
        audit(db, run, "mock_action", result)
        transition(db, run, "completed")
    except IntegrationError as exc:
        run.error = str(exc)
        transition(db, run, "failed")


def start(db, principal, payload: RequestInput, key: str):
    previous = db.scalar(
        select(Request).where(
            Request.tenant_id == principal.tenant_id, Request.idempotency_key == key
        )
    )
    if previous:
        if previous.payload != payload.model_dump():
            raise HTTPException(409, "Idempotency key was used with a different payload")
        return db.scalar(select(Run).where(Run.request_id == previous.id))
    tenant = db.get(Tenant, principal.tenant_id)
    policy = current_policy(db, tenant.id)
    request = Request(
        tenant_id=tenant.id,
        user_id=principal.user_id,
        idempotency_key=key,
        payload=payload.model_dump(),
    )
    db.add(request)
    db.flush()
    run = Run(
        tenant_id=tenant.id,
        request_id=request.id,
        policy_id=policy.id,
        state="received",
        prompt_version=PROMPT_VERSION,
    )
    db.add(run)
    db.flush()
    audit(db, run, "received", {"actor_id": principal.user_id})
    transition(db, run, "analyzing")
    started = perf_counter()
    try:
        record = MockIntegration(db).retrieve(tenant.id, payload.record_id)
        run.context = {"record": record, "policy": policy.rules, "policy_version": policy.version}
        audit(
            db,
            run,
            "tool_call",
            {
                "tool": "retrieve_context",
                "record_id": payload.record_id,
                "found": record is not None,
            },
        )
        try:
            rec, usage = AgentService().recommend(tenant.workflow, payload, run.context)
            for attr, value in usage.items():
                setattr(run, attr, value)
        except Exception:
            # Do not leak API responses or secrets into user-visible error fields.
            rec = Recommendation(
                classification="other",
                summary="Agent unavailable or invalid output; human review required.",
                response_draft="",
                uncertain=True,
            )
            run.model = "fallback"
            audit(
                db,
                run,
                "agent_fallback",
                {"reason": "Provider failure, refusal or invalid structured output"},
            )
        run.recommendation = rec.model_dump()
        run.decision = decide(tenant.workflow, policy.rules, payload, record, rec.uncertain)
        run.action = {
            "kind": run.decision["action"],
            "record_id": payload.record_id,
            "amount_cents": payload.amount_cents,
            "payment_method": "original",
        }
        run.action_hash = fingerprint(run.action, policy.id)
        audit(db, run, "policy_check", run.decision)
        if run.decision["outcome"] == "deny":
            transition(db, run, "rejected")
        elif run.decision["outcome"] == "review":
            transition(db, run, "awaiting_approval")
            db.add(
                Approval(
                    tenant_id=tenant.id,
                    run_id=run.id,
                    action_hash=run.action_hash,
                    policy_id=policy.id,
                    required_role=run.decision["required_role"],
                )
            )
        else:
            execute(db, run)
    except IntegrationError as exc:
        run.error = str(exc)
        transition(db, run, "failed")
    run.latency_ms = (perf_counter() - started) * 1000
    db.flush()
    return run


def decide_approval(db, principal, run_id, decision, note):
    run = db.scalar(
        select(Run).where(Run.id == run_id, Run.tenant_id == principal.tenant_id).with_for_update()
    )
    if not run:
        raise HTTPException(404, "Execution not found")
    approval = db.scalar(select(Approval).where(Approval.run_id == run.id).with_for_update())
    if not approval:
        raise HTTPException(409, "No approval requested")
    if principal.role != approval.required_role:
        raise HTTPException(403, "Approval role is not permitted")
    if run.state != "awaiting_approval" or approval.status != "pending":
        raise HTTPException(409, "Approval is no longer pending")
    # Rejection must remain available even if a source is down or a policy changed.
    if decision == "approve":
        policy = current_policy(db, run.tenant_id)
        if approval.policy_id != policy.id or approval.action_hash != fingerprint(
            run.action, policy.id
        ):
            raise HTTPException(409, "Policy or proposed action changed; submit a new request")
        request = db.get(Request, run.request_id)
        tenant = db.get(Tenant, run.tenant_id)
        record = MockIntegration(db).retrieve(run.tenant_id, request.payload["record_id"])
        fresh = decide(
            tenant.workflow,
            policy.rules,
            RequestInput.model_validate(request.payload),
            record,
            run.recommendation.get("uncertain", True),
        )
        if decision == "approve" and (
            fresh["outcome"] == "deny" or fresh["action"] != run.action["kind"]
        ):
            raise HTTPException(409, "Current source data no longer permits this action")
    from backend.db.models import now

    approval.status = "approved" if decision == "approve" else "rejected"
    approval.actor_id, approval.note, approval.decided_at = principal.user_id, note, now()
    audit(
        db,
        run,
        "approval_decision",
        {"decision": decision, "actor_id": principal.user_id, "note": note},
    )
    transition(db, run, approval.status)
    if decision == "approve":
        execute(db, run)
    db.flush()
    return run
