from collections import Counter, defaultdict

from sqlalchemy import select

from backend.db.models import Run
from backend.settings import settings


def metrics(db, tenant_id):
    runs = list(db.scalars(select(Run).where(Run.tenant_id == tenant_id)))
    counts = Counter(run.state for run in runs)
    activity = defaultdict(lambda: {"processed": 0, "completed": 0})
    for run in runs:
        day = run.created_at.strftime("%Y-%m-%d")
        activity[day]["processed"] += 1
        activity[day]["completed"] += run.state == "completed"
    config = settings()
    return {
        "total_requests": len(runs),
        "awaiting_approval": counts["awaiting_approval"],
        "completed": counts["completed"],
        "escalation_rate": sum(r.decision.get("outcome") == "review" for r in runs) / len(runs)
        if runs
        else None,
        "average_latency_ms": sum(r.latency_ms for r in runs) / len(runs) if runs else None,
        "estimated_cost": sum(r.estimated_cost for r in runs),
        "tokens": sum(r.input_tokens + r.output_tokens for r in runs),
        "cost_configured": config.input_cost_per_million > 0 or config.output_cost_per_million > 0,
        "activity": [{"date": day, **values} for day, values in sorted(activity.items())],
        "states": dict(counts),
    }
