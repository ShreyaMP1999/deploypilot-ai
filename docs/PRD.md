# Product requirements · DeployPilot AI

## Problem and positioning
Enterprise teams repeatedly rebuild similar automations because refund rules, support permissions and approval responsibilities differ by customer. DeployPilot demonstrates one configurable application that keeps these differences explicit and observable. It is an operations console, not a general-purpose chatbot.

## Personas and jobs to be done
| Persona | Job | Evidence in the MVP |
|---|---|---|
| Customer operations manager | Resolve eligible refunds without losing financial control | Order lookup, amount limits, approval queue and audit history |
| Security reviewer | Triage account recovery without giving an LLM account privileges | Security-only review; simulated escalation, never credential changes |
| Forward deployed engineer | Adapt the same core to customer requirements | Versioned tenant policies, integration adapters and reproducible demo |
| AI product owner | Decide whether automation is safe enough to expand | Labeled policy suite, persisted evaluation history and execution metrics |

## Customer scenarios and user journeys
Northstar Commerce: authenticate → select a synthetic order → enter amount and explanation → inspect context and recommendation → enforce 30-day window and remaining balance → review amounts above $100 → execute a database-only refund → inspect trace.

OrbitCloud SaaS: switch authorized customer → select a ticket → classify a support request → retrieve policy and identity context → require security review for privileged or uncertain requests → record an escalation without changing credentials. Documentation requests produce a mock response draft.

## MVP requirements
- One reusable workflow orchestrator with persisted states and guarded transitions.
- Authentication and server-validated membership; no tenant scope supplied in workflow bodies.
- Policy decisions remain independent of model authority; human approval cannot override a denial.
- Explicit requested amount and source record fields make financial proposals unambiguous.
- Six console views with functional loading, empty, failure and result states.
- Tenant-scoped metrics derived from persisted runs; evaluation metrics distinguish unmeasured values.
- Offline operation without an API key; opt-in structured model recommendations with read-only context tooling.

## MVP definition and non-goals
The portfolio MVP covers two synthetic customer configurations, local persistence and mock side effects. It does not promise real payment integration, SSO, regulatory certification, production SLAs, credential recovery, autonomous policy changes or customer onboarding UI. The console's six views share one Next.js route; route persistence and deep links are future work.

## Success metrics and gates
Safety gates: no financial over-refund, no cross-tenant reads, no unauthorized approval and no duplicate simulated action in the tested scenarios. Every pending approval binds a policy version and action hash. Policy and adapter cases must match their independent labels.

Product metrics: completed workflows / requests, escalation rate, average processing latency, tokens and configured model-cost estimate. A high completion rate alone is not success: correctly rejected requests and captured approvals are essential. No claimed labor savings are derived from synthetic traffic.

Before a real pilot: collect at least 200 representative de-identified requests per workflow, agree on acceptable false approvals with the customer, review labels with operations/security owners and evaluate shadow decisions. Measure handling time against a human baseline before proposing ROI.

## Assumptions and risks
The synthetic order/ticket is trusted context; the request text is untrusted. Operators already have customer authorization. Demo authentication is intentionally small and has no password recovery. Policy modifications occur through reviewed migrations or operator code, not the UI. Model output may be incorrect, refused or delayed; fallback creates review work. Synchronous model calls hold a transaction and limit throughput. Deployment, accessibility and security controls need further hardening before handling real customer data.
