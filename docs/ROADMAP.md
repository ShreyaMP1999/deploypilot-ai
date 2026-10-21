# Roadmap

| Horizon | Priority | Rationale | Impact | Effort | Acceptance gate |
|---|---|---|---|---|---|
| Now | Reproducible local demo and passing policy/security tests | Establish trustworthy behavior before external integrations | High | Medium | Both tenant journeys, migrations, build and guarded approval tests pass |
| Now | Transparent evaluation and cost labeling | Prevent synthetic results being mistaken for production evidence | High | Low | Unmeasured metrics are null and offline mode is visible |
| Next | OIDC, secure server sessions, reviewer separation | Replace seeded credentials and permit enterprise access lifecycle | High | High | SSO integration, revocation and role escalation tests |
| Next | Durable worker and outbox | Shorten API transactions and safely integrate real side effects | High | High | Crash recovery and provider idempotency verified |
| Next | Policy draft/test/publish flow | Give customer owners controlled configuration autonomy | High | Medium | Versioned changes invalidate stale approvals; comparison report required |
| Next | Live model dataset expansion and baseline comparison | Measure language understanding and drift | High | Medium | Reviewed labels, model/prompt provenance, failure analysis and agreed gates |
| Next | Database RLS and audit retention | Strengthen defense in depth and data lifecycle | High | Medium | Tenant isolation under direct SQL application role and retention tests |
| Later | Zendesk / Salesforce support adapter | Meet customers inside their support workflow | Medium | High | Permission mapping, webhook integrity and reconciliation |
| Later | Shopify / Stripe sandbox adapter | Validate real-world financial orchestration | High | High | Outbox, partial failure recovery, ledger reconciliation and human sign-off |
| Later | Langfuse or OpenTelemetry export | Improve provider-level traces and cost reconciliation | Medium | Medium | Redaction and retention verified |
| Later | Workflow-specific SLOs, pagination and analytics aggregation | Support workloads beyond a small portfolio dataset | Medium | Medium | Load tests and query budgets met |

Enterprise-readiness gaps include SSO, distributed rate limits, request-body limits at an ingress, secrets rotation, fine-grained source-record ownership, disaster recovery, independent security review, tamper-resistant audit storage and live integration monitoring. These are future work rather than implied features.
