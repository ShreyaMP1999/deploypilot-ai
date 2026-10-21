import json
import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic, perf_counter

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi import Request as HTTPRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend import auth
from backend.analytics import metrics
from backend.db.models import (
    Action,
    Approval,
    Audit,
    Configuration,
    EvaluationRun,
    Membership,
    Record,
    Request,
    Run,
    Tenant,
)
from backend.db.session import get_db
from backend.schemas import ApprovalInput, LoginInput, RequestInput, SwitchInput
from backend.settings import settings
from backend.workflows.service import current_policy, decide_approval, start

logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(title="DeployPilot AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
limiter = defaultdict(deque)
limiter_lock = Lock()


@app.middleware("http")
async def rate_limit_and_log(request: HTTPRequest, call_next):
    # Single-process demo limiter; deploy behind a shared gateway for multiple workers.
    started = perf_counter()
    ip = request.client.host if request.client else "unknown"
    key = (ip, "login" if request.url.path == "/auth/login" else "api")
    now = monotonic()
    with limiter_lock:
        for stale in [k for k, v in limiter.items() if not v or now - v[-1] > 60]:
            del limiter[stale]
        if key not in limiter and len(limiter) >= 10000:
            return JSONResponse({"detail": "Rate limiter capacity reached"}, status_code=429)
        bucket = limiter[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= (10 if key[1] == "login" else 120):
            return JSONResponse(
                {"detail": "Rate limit exceeded; retry in one minute"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        bucket.append(now)
    response = await call_next(request)
    logging.getLogger("deploypilot.http").info(
        json.dumps(
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round((perf_counter() - started) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(IntegrityError)
async def conflict(_, exc):
    return JSONResponse(
        {"detail": "Concurrent or duplicate operation; retry with the same idempotency key"},
        status_code=409,
    )


@app.exception_handler(Exception)
async def internal_error(_, exc):
    logging.getLogger("deploypilot").error(
        json.dumps({"event": "unhandled_error", "type": type(exc).__name__})
    )
    return JSONResponse(
        {"detail": "Operation failed safely. Check server diagnostics."}, status_code=500
    )


@app.get("/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "agent_mode": settings().agent_mode, "integrations": "simulated"}


@app.post("/auth/login")
def login(payload: LoginInput, db=Depends(get_db)):
    return auth.login(db, payload.username, payload.password, payload.tenant_id)


@app.post("/auth/switch")
def switch(payload: SwitchInput, p=Depends(auth.authenticate), db=Depends(get_db)):
    if not db.get(Membership, (p.user_id, payload.tenant_id)):
        raise HTTPException(403, "Customer membership required")
    return {"access_token": auth.issue_token(p.user_id, payload.tenant_id), "token_type": "bearer"}


@app.get("/me")
def me(p=Depends(auth.authenticate), db=Depends(get_db)):
    return {"tenant_id": p.tenant_id, "role": p.role, "user_id": p.user_id}


@app.get("/tenants")
def tenants(p=Depends(auth.authenticate), db=Depends(get_db)):
    memberships = db.scalars(select(Membership).where(Membership.user_id == p.user_id))
    return [{"id": m.tenant_id, "name": db.get(Tenant, m.tenant_id).name} for m in memberships]


@app.get("/configuration")
def configuration(p=Depends(auth.authenticate), db=Depends(get_db)):
    tenant = db.get(Tenant, p.tenant_id)
    config = db.get(Configuration, p.tenant_id)
    policy = current_policy(db, p.tenant_id)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "industry": tenant.industry,
        "workflow": tenant.workflow,
        "integrations": config.integrations,
        "environment": config.environment,
        "policy": policy.rules,
        "policy_version": policy.version,
        "agent_mode": settings().agent_mode,
    }


@app.get("/records")
def records(p=Depends(auth.authenticate), db=Depends(get_db)):
    return [
        {"id": r.id, **r.data, "refunded_cents": r.refunded_cents}
        for r in db.scalars(
            select(Record).where(Record.tenant_id == p.tenant_id).order_by(Record.id)
        )
    ]


@app.get("/metrics")
def analytics(p=Depends(auth.authenticate), db=Depends(get_db)):
    return metrics(db, p.tenant_id)


def serialize(db, run):
    request = db.get(Request, run.request_id)
    approval = db.scalar(select(Approval).where(Approval.run_id == run.id))
    action = db.scalar(select(Action).where(Action.run_id == run.id))
    events = list(
        db.scalars(
            select(Audit)
            .where(Audit.run_id == run.id, Audit.tenant_id == run.tenant_id)
            .order_by(Audit.created_at, Audit.id)
        )
    )
    return {
        "id": run.id,
        "tenant_id": run.tenant_id,
        "state": run.state,
        "request": request.payload,
        "created_at": run.created_at.isoformat(),
        "context": run.context,
        "recommendation": run.recommendation,
        "decision": run.decision,
        "action": run.action,
        "result": action.result if action else None,
        "approval": {
            "id": approval.id,
            "status": approval.status,
            "required_role": approval.required_role,
            "note": approval.note,
            "actor_id": approval.actor_id,
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        }
        if approval
        else None,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "latency_ms": run.latency_ms,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "estimated_cost": run.estimated_cost,
        "error": run.error,
        "events": [
            {
                "id": e.id,
                "event": e.event,
                "detail": e.detail,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


@app.get("/runs")
def runs(p=Depends(auth.authenticate), db=Depends(get_db)):
    return [
        serialize(db, r)
        for r in db.scalars(
            select(Run)
            .where(Run.tenant_id == p.tenant_id)
            .order_by(Run.created_at.desc())
            .limit(100)
        )
    ]


@app.get("/runs/{run_id}")
def run_detail(run_id: str, p=Depends(auth.authenticate), db=Depends(get_db)):
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == p.tenant_id))
    if not run:
        raise HTTPException(404, "Execution not found")
    return serialize(db, run)


@app.post("/runs", status_code=201)
def execute(
    payload: RequestInput,
    idempotency_key: str = Header(min_length=8, max_length=100),
    p=Depends(auth.authenticate),
    db=Depends(get_db),
):
    if p.role == "viewer":
        raise HTTPException(403, "Viewer cannot start workflows")
    run = start(db, p, payload, idempotency_key)
    db.commit()
    return serialize(db, run)


@app.post("/runs/{run_id}/approval")
def approval(run_id: str, payload: ApprovalInput, p=Depends(auth.authenticate), db=Depends(get_db)):
    run = decide_approval(db, p, run_id, payload.decision, payload.note)
    db.commit()
    return serialize(db, run)


@app.get("/evaluations")
def evaluations(p=Depends(auth.authenticate), db=Depends(get_db)):
    return [
        {
            "id": e.id,
            "model": e.model,
            "prompt_version": e.prompt_version,
            "results": e.results,
            "created_at": e.created_at.isoformat(),
        }
        for e in db.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.tenant_id == p.tenant_id)
            .order_by(EvaluationRun.created_at.desc())
            .limit(20)
        )
    ]


@app.post("/evaluations", status_code=201)
def run_evaluations(p=Depends(auth.authenticate), db=Depends(get_db)):
    if p.role == "viewer":
        raise HTTPException(403, "Viewer cannot run evaluations")
    from backend.evaluations.runner import evaluate

    result = evaluate(db, p.tenant_id)
    db.commit()
    return result
