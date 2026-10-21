"""Read-only evaluation harness: never executes business actions."""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

from backend.agents.service import PROMPT_VERSION, AgentService
from backend.db.models import EvaluationCase, EvaluationRun
from backend.db.session import SessionLocal
from backend.integrations.mock import IntegrationError, MockIntegration
from backend.policies.engine import decide
from backend.schemas import RequestInput
from backend.settings import settings

ROOT = Path(__file__).resolve().parents[2]
RULES = {"refund_window_days": 30, "approval_threshold_cents": 10000}


def build_case(case):
    payload = RequestInput(
        text=case.get("text", "Please refund my purchase."),
        record_id="EVAL-SYNTHETIC",
        amount_cents=case.get("amount_cents"),
        payment_method=case.get("payment_method", "original"),
    )
    record = (
        None
        if case.get("missing")
        else {
            "total_cents": 18900,
            "refunded_cents": case.get("refunded_cents", 0),
            "purchased_at": (date.today() - timedelta(days=case.get("age_days", 7))).isoformat(),
            "status": case.get("status", "delivered"),
            "privileged": case.get("privileged", False),
            "identity_verified": case.get("identity_verified", True),
            "category": case.get("record_category", "documentation"),
        }
    )
    return payload, record


def run_case(case, live=False):
    payload, record = build_case(case)
    workflow = "refund" if case["tenant_id"] == "northstar" else "support"
    usage = {"input_tokens": 0, "output_tokens": 0, "estimated_cost": 0}
    classification = None
    if case.get("adapter_failure"):
        # Exercise the actual adapter failure path without changing any seeded source record.
        class UnavailableDB:
            def get(self, *args):
                return SimpleNamespace(data={"tool_failure": True})

        try:
            MockIntegration(UnavailableDB()).retrieve(case["tenant_id"], payload.record_id)
        except IntegrationError:
            return "failed", classification, usage
        return "unexpected_success", classification, usage
    uncertain = case.get("uncertain", False)
    if live:
        rec, usage = AgentService().recommend(
            workflow, payload, {"record": record, "policy": RULES}
        )
        classification, uncertain = rec.classification, rec.uncertain
    outcome = decide(workflow, RULES, payload, record, uncertain)["outcome"]
    return outcome, classification, usage


def evaluate(db, tenant_id, live=False):
    cases = [
        c
        for c in json.loads((ROOT / "evaluations/cases.json").read_text())
        if c["tenant_id"] == tenant_id
    ]
    if live and (settings().agent_mode != "live" or not settings().openai_api_key):
        raise ValueError("Live evaluation requires AGENT_MODE=live and OPENAI_API_KEY")
    started = perf_counter()
    failures = []
    review_count = captured = policy_count = policy_passed = classification_count = (
        classification_passed
    ) = 0
    tokens = 0
    cost = 0
    for case in cases:
        if not db.get(EvaluationCase, case["id"]):
            db.add(EvaluationCase(id=case["id"], tenant_id=tenant_id, data=case))
        try:
            actual, classification, usage = run_case(case, live)
        except Exception:
            actual, classification, usage = (
                "agent_error",
                None,
                {"input_tokens": 0, "output_tokens": 0, "estimated_cost": 0},
            )
        tokens += usage["input_tokens"] + usage["output_tokens"]
        cost += usage["estimated_cost"]
        if not case.get("adapter_failure"):
            policy_count += 1
            policy_passed += actual == case["expected"]
        if case["expected"] == "review":
            review_count += 1
            captured += actual == "review"
        if live and "expected_classification" in case:
            classification_count += 1
            classification_passed += classification == case["expected_classification"]
        if actual != case["expected"]:
            failures.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "expected": case["expected"],
                    "actual": actual,
                }
            )
    result = {
        "total": len(cases),
        "passed": len(cases) - len(failures),
        "decision_accuracy": policy_passed / policy_count,
        "approval_capture_rate": captured / review_count if review_count else None,
        "classification_accuracy": classification_passed / classification_count
        if classification_count
        else None,
        "unauthorized_action_rate": None,
        "workflow_completion_rate": None,
        "average_latency_ms": (perf_counter() - started) * 1000 / len(cases),
        "tokens": tokens,
        "estimated_cost": cost,
        "llm_status": "run" if live else "not_run",
        "failures": failures,
        "scope": "read-only recommendations and policy decisions; no actions executed",
        "dataset_version": "v1-60",
    }
    run = EvaluationRun(
        tenant_id=tenant_id,
        model=settings().openai_model if live else "deterministic-policy",
        prompt_version=PROMPT_VERSION,
        results=result,
    )
    db.add(run)
    db.flush()
    return {
        "id": run.id,
        "tenant_id": tenant_id,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "created_at": run.created_at.isoformat(),
        "results": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Makes paid API calls; otherwise pure deterministic evaluation",
    )
    parser.add_argument("--output", default="evaluations/reports")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with SessionLocal.begin() as db:
        runs = [evaluate(db, tenant, args.live) for tenant in ("northstar", "orbit")]
    (output / "latest.json").write_text(json.dumps(runs, indent=2) + "\n")
    lines = [
        "# Measured evaluation results",
        "",
        f"Mode: {'live LLM' if args.live else 'deterministic; LLM not run'}",
        "",
        "| Customer | Passed | Decision accuracy | Approval capture | Latency / case |",
        "|---|---:|---:|---:|---:|",
    ]
    for run in runs:
        r = run["results"]
        lines.append(
            f"| {run['tenant_id']} | {r['passed']}/{r['total']} | {r['decision_accuracy']:.1%} | {r['approval_capture_rate']:.1%} | {r['average_latency_ms']:.3f} ms |"
        )
    lines += [
        "",
        "These are synthetic policy/adapter checks, not production or LLM benchmarks. No business actions are executed.",
        "Classification accuracy, unauthorized action rate and completion rate are unmeasured (null) in deterministic mode.",
    ]
    (output / "latest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if any(r["results"]["failures"] for r in runs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
