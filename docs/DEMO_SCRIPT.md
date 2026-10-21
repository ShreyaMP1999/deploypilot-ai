# Demo script

All customers, orders, tickets and effects are synthetic. Start from a newly seeded database so the example orders have their full refundable balance. A completed refund consumes that synthetic balance; repeating it is correctly denied when insufficient balance remains.

## 90-second narrated walkthrough
**0–12 seconds:** “DeployPilot is one operations control center for customer-specific AI workflows. I am signed into Northstar Commerce. The metrics come from this local environment, and the badge clearly shows whether recommendations are offline or use a model.”

**12–37 seconds:** Open Workflow Studio and choose Approval example (`ORD-1001`, $149). Execute. “The assistant recommends; the backend decides. We retrieve the order and versioned policy. This refund is within 30 days and below purchase value, but above the $100 manager threshold.”

**37–52 seconds:** Open Approval Center, add a review note and click Approve & process. “The server verifies my manager role, locks the request, checks the action fingerprint and current policy, then records a simulated refund exactly once.” Inspect the final result.

**52–72 seconds:** Switch to OrbitCloud, open Workflow Studio and execute the privileged recovery example. “The same application now uses support records and security policy. Approval only creates a simulated escalation. No credential-reset tool is available.” Approve in the security queue.

**72–90 seconds:** Open Evaluations and run the policy suite. Then inspect Execution Logs. “These are measured synthetic policy checks, with model evaluation explicitly marked not run. Every state transition, policy check, human review and final action can be inspected.”

## Longer technical interview demo
1. Explain the PRD's customer-specific rules and the shared architecture diagram.
2. Run the automatic Northstar example (`ORD-1002`, $49) and inspect the refund record. A second excessive refund is rejected by remaining balance.
3. Run the approval example on an unused odd-numbered order. Inspect the policy version and manager role before deciding.
4. Sign out and authenticate as `analyst` using the seeded password. Read the logs; observe execution and approval controls disabled. The API independently returns 403 for those operations.
5. Switch tenants as `pilot` and inspect changed records, policies and metrics. Show API tests that return 404 for another tenant's run.
6. Run Orbit's privileged recovery and ordinary documentation examples. Explain why an approved security request still cannot reset credentials.
7. Inspect tests for stale policies, action mutation, prompt injection, provider failure and PostgreSQL concurrent approval/refund races.
8. Run `python -m backend.evaluations.runner`, explain 60 labels, null unmeasured values and the distinction between policy checks and LLM accuracy.
9. Explain the transaction boundary and why real payments need an outbox, provider idempotency and reconciliation.
10. Finish with the roadmap's adoption gates and how handling-time improvements would be measured with a real customer.

## Browser verification
With fresh seeded servers at ports 8000 and 3000:

```bash
cd apps/web
npx playwright install chromium
# Supply the seeded password through your environment, then:
node tests/smoke.mjs
```

This script validates login, both tenant journeys, approval effects, automatic flows, evaluations, configurations, log isolation and a mobile viewport, and saves screenshots in `demo/`. Do not run it against production or a database with valuable data; the flows deliberately consume synthetic refund balances.

Video: **placeholder — no recording published.** Hosted demo: **placeholder — not deployed.**
