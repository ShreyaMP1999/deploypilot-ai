# Evaluation and verification report

Observed on **2026-10-21**. These are synthetic local results, not real customer outcomes. No live LLM benchmark, production deployment or financial integration is claimed.

## Methodology
`evaluations/cases.json` contains 60 independently labeled cases, 30 per customer. The harness invokes the real pure policy function and, for four source-outage cases, the actual mock adapter's failure branch. Expected outcomes are stored in the dataset, not calculated from the function under test. The dataset includes standard requests, amount and date boundaries, over-refunds, missing information, uncertain recommendations, wrong payment methods, privileged requests, identity uncertainty, prompt injections and source failures.

The API suite separately executes persisted workflows, approval/rejection and simulated side effects. PostgreSQL concurrency tests synchronize two sessions to demonstrate that competing refunds cannot exceed the balance and duplicate approval attempts produce exactly one action. SQLite skips those two tests because it does not provide PostgreSQL row-lock semantics.

## Measured results
| Check | Observed result | Environment |
|---|---|---|
| Final backend suite | **90 passed** | Python 3.13 container, PostgreSQL 18 |
| Final SQLite suite | **88 passed, 2 skipped** | Local Python 3.13; concurrency tests intentionally skipped |
| Earlier PostgreSQL run before final rejection-outage regression | 89 passed | Native PostgreSQL 15 |
| Northstar policy/adapter labels | **30/30 matched** | Deterministic evaluation, PostgreSQL 18-backed history |
| Orbit policy/adapter labels | **30/30 matched** | Deterministic evaluation, PostgreSQL 18-backed history |
| Decision accuracy | 100% of the 56 pure-policy labels | Synthetic deterministic cases only |
| Approval capture | 100% of labeled review cases | Synthetic deterministic cases only |
| Frontend production build | Passed | Next.js 16.4.2, Node 24; native and Docker builds |
| TypeScript validation | Passed | `npm run typecheck` |
| Backend lint | Passed | `ruff check backend apps/api tests` |
| Migration check | No model/schema drift | Alembic on SQLite, native PostgreSQL and container PostgreSQL |
| Migration lifecycle | Upgrade → downgrade → upgrade → seed passed | Disposable native PostgreSQL database |
| Compose packaging | API/web images built; DB/API/web healthy | Docker Desktop, PostgreSQL 18 |
| Browser journeys | Passed, no page errors | Chromium / packaged Compose application |
| Mobile layout | Passed at 390 × 844; no document horizontal overflow | Chromium |
| Live model evaluation | **Not run** | No API key configured |
| Public deployment | **Not performed** | No hosting credentials or publication used |

Detailed observed run IDs, timestamps, latency and failures are in [measured JSON](../evaluations/reports/latest.json) and [measured Markdown](../evaluations/reports/latest.md). Latencies vary by environment and include harness overhead; they are not production model latency estimates.

## Commands actually exercised
```bash
alembic upgrade head
python -m backend.db.seed
ruff check backend apps/api tests
pytest -q
# Also ran pytest with TEST_DATABASE_URL pointing at a disposable native PostgreSQL DB.
python -m backend.evaluations.runner
alembic check
npm --prefix apps/web run build
npm --prefix apps/web run typecheck
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 240
# PostgreSQL 18 suite used a separate deploypilot_test DB and mounted tests read-only:
docker compose run --rm --no-deps -e PYTHONPATH=/app -v "$PWD/tests:/app/tests:ro" api sh -c 'export TEST_DATABASE_URL="${DATABASE_URL%/deploypilot}/deploypilot_test"; pytest -q /app/tests'
# With matching DEMO_PASSWORD supplied in the environment, from apps/web:
node tests/smoke.mjs
```

## Security and reliability coverage
Unauthenticated/forged sessions; revoked tenant membership; cross-tenant records, traces and approvals; read-only users attempting execution/approval; input validation and forbidden fields; idempotency key reuse; approval replay; rejected requests never executing; changed policy version; mutated action; expired source at review; remaining balance after previous refunds; tool failure; malformed structured output; safe provider fallback; injection requesting limit bypass; source outage during rejection; invalid state transitions; derived analytics; evaluation tenant scope; login throttling; actual concurrent refunds and approvals.

The browser script verifies login, the Northstar approval and automatic examples, security-reviewed Orbit recovery, documentation drafting, customer switching, configuration changes, tenant-specific logs, evaluation execution and responsive rendering. Screenshots in `demo/` were captured from these real synthetic runs.

## Failure modes found and corrected
- A wrapping source-record label made the exact accessible name include option contents. An explicit accessible label resolved selection and keyboard-test ambiguity.
- An absolutely positioned screen-reader table heading escaped the mobile scroll container, creating document overflow. Positioning the table wrapper contains it.
- The initial rejection path fetched source context even when the action was being rejected. Revalidation now occurs only before approval; rejection remains possible during a source outage. A regression test verifies that no action executes.

## Interpretation limits
Classification accuracy is null in deterministic reports because the policy harness does not measure language understanding. Unauthorized action rate and workflow completion rate are also null because the read-only harness never executes actions. API tests establish correctness in the enumerated scenarios, not a statistically representative production rate. Token usage and model cost are zero for offline runs because no model is called.

Live evaluation is opt-in with `AGENT_MODE=live`, a backend API key and `python -m backend.evaluations.runner --live`. It records structured classification, decision outcomes, tokens, cost and model/prompt provenance without executing actions. Dataset prompt version is `v1`; baseline/revised prompt comparison UI is not implemented. Partial provider failures may undercount billable usage; use provider usage reconciliation before financial reporting.

## Next steps
Expand independent customer labels; evaluate live recommendations; test refusals, latency and prompt drift at scale; add multi-model baselines, reviewer agreement, load tests and retention controls. Agree on acceptable error costs with customer operators before an external pilot. CI is configured to repeat backend, frontend and container checks; remote CI status must be checked independently after pushing.
