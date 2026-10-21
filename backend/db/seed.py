"""Idempotent synthetic seed. Run migrations first; this never creates schema."""

import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from backend.db.models import Configuration, Membership, Policy, Record, Tenant, User
from backend.db.session import SessionLocal
from backend.settings import settings

ROOT = Path(__file__).resolve().parents[2]


def seed(db):
    from backend.auth import hash_password

    for item in json.loads((ROOT / "configs/tenants.json").read_text()):
        if db.get(Tenant, item["id"]):
            continue
        db.add(Tenant(**{k: item[k] for k in ("id", "name", "industry", "workflow")}))
        db.flush()
        db.add(Configuration(tenant_id=item["id"], integrations=item["integrations"]))
        db.add(Policy(tenant_id=item["id"], version=1, rules=item["rules"]))
    db.flush()
    for username in ("pilot", "analyst"):
        if db.scalar(select(User).where(User.username == username)):
            continue
        user = User(username=username, password_hash=hash_password(settings().demo_password))
        db.add(user)
        db.flush()
        for tenant, role in (("northstar", "manager"), ("orbit", "security")):
            db.add(
                Membership(
                    user_id=user.id,
                    tenant_id=tenant,
                    role=role if username == "pilot" else "viewer",
                )
            )
    for i in range(1, 25):
        order_id = f"ORD-{1000 + i}"
        if not db.get(Record, ("northstar", order_id)):
            db.add(
                Record(
                    tenant_id="northstar",
                    id=order_id,
                    kind="order",
                    data={
                        "customer": f"Synthetic customer {i:02}",
                        "total_cents": 18900 if i % 2 else 7900,
                        "purchased_at": (
                            date.today() - timedelta(days=45 if i % 5 == 0 else 7)
                        ).isoformat(),
                        "status": "pending" if i % 7 == 0 else "delivered",
                        "payment_method": "original",
                    },
                )
            )
        ticket_id = f"TKT-{2000 + i}"
        if not db.get(Record, ("orbit", ticket_id)):
            db.add(
                Record(
                    tenant_id="orbit",
                    id=ticket_id,
                    kind="ticket",
                    data={
                        "customer": f"Fictional workspace {i:02}",
                        "privileged": bool(i % 2),
                        "identity_verified": i % 5 != 0,
                        "category": "security" if i % 2 else "documentation",
                        "knowledge_base": "API documentation: use a scoped token. Privileged access recovery must be reviewed by security.",
                    },
                )
            )
    db.flush()


if __name__ == "__main__":
    with SessionLocal.begin() as db:
        seed(db)
    print("Seeded 2 tenants, 2 users and 48 synthetic integration records.")
