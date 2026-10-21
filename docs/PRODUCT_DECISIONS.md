# Product decisions

| Decision | Rationale | Trade-off / trigger to revisit |
|---|---|---|
| Modular monolith | One deployable backend keeps tenant context, approvals and transactions understandable to a small team | Extract workers when provider latency or throughput becomes material |
| One focused recommendation assistant | Refund and support workflows share intake, context, recommendation and policy stages; multiple autonomous agents add coordination without solving a demonstrated problem | Add specialists only after evaluations reveal a measurable benefit |
| Deterministic enforcement | Monetary rules and permissions must be reproducible and testable outside a probabilistic model | Some ambiguous requests require humans rather than speculative automation |
| Human approvals | Financial thresholds and privileged access need explicit accountability | Review queues introduce latency; measure workload and tune policy with customer owners |
| Configuration-driven customer deployment | Tenant policy versions and adapters express customer differences without forks | Policy authoring remains an engineering task in this MVP |
| Mock integrations | Recruiters can reproduce the complete safety flow without payments, enterprise credentials or sensitive data | Synthetic results do not prove real integration reliability or business impact |
| Explicit amount and source fields | Financial proposals remain unambiguous even when free text contains conflicting amounts | Natural-language extraction can later prefill fields but must require confirmation |
| Responses API with a bounded tool | The needed loop has one read-only context tool and one strict recommendation, so a full Agents SDK runtime adds little value | Revisit SDK adoption for durable agent sessions and richer tracing |
| Read-only policy console | Avoid introducing casual policy changes without version review and migration tests | Add policy draft, test, compare and publish workflow before live customer onboarding |
| Memory-only browser sessions | Avoid persistent bearer tokens in a small demonstration | Page refresh requires login; replace with enterprise OIDC and secure sessions for production |

The target user is an operator deciding what may execute, not a user watching an AI chat. The interface therefore separates the model recommendation, deterministic decision, human approval and final action. Ambiguous context produces an escalation task rather than a plausible-looking refund.
