"""Pure policy functions. LLM text cannot grant an action or change monetary limits."""

import re
from datetime import date

from backend.schemas import RequestInput

SECURITY = re.compile(
    r"admin|privileg|password|credential|reset|recover|mfa|2fa|token|secret|disable|bypass|ignore",
    re.IGNORECASE,
)


def decide(
    workflow: str,
    rules: dict,
    request: RequestInput,
    record: dict | None,
    uncertain: bool = False,
    today: date | None = None,
) -> dict:
    def result(outcome, reason, kind, role=None):
        return {"outcome": outcome, "reason": reason, "action": kind, "required_role": role}

    if record is None:
        return result(
            "review",
            "Unknown record; retrieve verified context before acting.",
            "route_review",
            "manager" if workflow == "refund" else "security",
        )
    if workflow == "refund":
        role = "manager"
        if request.amount_cents is None:
            return result("review", "Refund amount is missing.", "route_review", role)
        if request.payment_method != "original":
            return result("deny", "Refunds must use the original payment method.", "none")
        age = ((today or date.today()) - date.fromisoformat(record["purchased_at"])).days
        if age < 0 or age > rules["refund_window_days"]:
            return result("deny", "Order is outside the refund window.", "none")
        if request.amount_cents > record["total_cents"] - record.get("refunded_cents", 0):
            return result("deny", "Amount exceeds the remaining purchase balance.", "none")
        if record.get("status") != "delivered":
            return result("review", "Order delivery is not confirmed.", "route_review", role)
        if uncertain or request.amount_cents > rules["approval_threshold_cents"]:
            return result(
                "review", "Manager review required by amount or agent uncertainty.", "refund", role
            )
        return result("allow", "Within window, balance and automatic approval threshold.", "refund")
    if not record.get("identity_verified"):
        return result(
            "review",
            "Identity is unverified; no account change is permitted.",
            "route_review",
            "security",
        )
    if record.get("privileged") or SECURITY.search(request.text):
        return result(
            "review",
            "Privileged recovery requires security review. Only escalation may execute.",
            "escalate_access",
            "security",
        )
    if record.get("category") != "documentation" or uncertain:
        return result(
            "review",
            "Non-documentation or uncertain request requires review.",
            "route_review",
            "security",
        )
    return result(
        "allow", "Documentation response draft only; no credential modification.", "draft_response"
    )
