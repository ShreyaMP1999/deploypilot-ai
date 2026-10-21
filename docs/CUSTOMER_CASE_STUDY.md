# Fictional deployment case study · Northstar Commerce

**This is a simulated customer scenario using fictional records. It is not a real engagement, measured customer outcome or testimonial.**

## Requirements and pain points
Imagine a mid-sized commerce operation with inconsistent refund handling across support agents. Managers need a 30-day window, a $100 approval threshold, a purchase-balance ceiling and refunds to the original payment method. Support staff need a clear explanation instead of an opaque automation decision. Security reviewers must be able to reconstruct who approved an action.

## Proposed solution and integration strategy
Deploy one configured instance of the shared refund workflow. An order adapter supplies purchase date, value, delivery status and already-refunded balance. The recommendation assistant summarizes the customer's request. A deterministic policy service decides what is allowed and the manager queue handles larger refunds. Approved actions are recorded by the simulated refund adapter.

The adapter protocol isolates source retrieval and action execution. A real rollout would require merchant-side customer identity mapping, reconciliation of the authoritative refund balance, payment provider idempotency, signed webhooks and a transactional outbox. None of these external integrations is claimed as implemented here.

## Simulated deployment process
1. Translate customer rules into `configs/tenants.json` and a versioned policy row.
2. Run migrations and seed synthetic orders. Confirm tenant membership and reviewer roles.
3. Execute labeled boundary cases at 30 days, $100 and remaining purchase value.
4. Demonstrate a $149 manager-reviewed refund and a $49 automatic refund.
5. Inspect the audit history and attempt a duplicate approval and a cross-tenant lookup.
6. Agree on a shadow-mode pilot and a rollback plan before connecting real systems.

## Evaluation methodology
Use independently labeled policy cases, API authorization tests and real PostgreSQL concurrency tests. In this implementation all 60 deterministic policy/adapter labels match; these are synthetic checks rather than an estimate of real-world AI accuracy. Live LLM recommendations have not been evaluated without a configured key. See the measured report and test coverage for precise scope.

## Expected business value and how to validate it
Hypothesis: low-risk refunds can reduce handling time while managers retain authority over expensive actions. Do not assign a percentage savings from this demo. In a real pilot, compare median handling time and rework rate with the previous human workflow, measure reviews captured, and reconcile every executed refund against the merchant ledger.

## Future improvements
Customer SSO, least-privilege database roles, policy publishing with shadow evaluation, asynchronous workers, real payment reconciliation and reviewer delegation. OrbitCloud uses the same architecture with security-specific routing, showing configuration reuse across different industries without claiming that account recovery itself is automated.
