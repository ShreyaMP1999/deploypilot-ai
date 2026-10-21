# Running and deploying DeployPilot

## Local Docker setup
Install Docker Desktop / Docker Engine with Compose. Copy `.env.example` to `.env`. Replace `JWT_SECRET` with at least 32 random characters and `DEMO_PASSWORD` with a chosen demo password of at least 12 characters. Generate the secret with `python -c 'import secrets; print(secrets.token_hex(32))'`. Set `POSTGRES_PASSWORD` to a URL-safe password (hex is convenient); Compose embeds it in the database URL.

```bash
docker compose config --quiet
docker compose up --build -d --wait
# Console: http://localhost:3000   API docs: http://localhost:8000/docs
docker compose exec api python -m backend.evaluations.runner
docker compose logs -f api
# Stop while preserving the database:
docker compose down
```

The API runs Alembic and the idempotent synthetic seed on startup. PostgreSQL 18 uses a volume mounted at `/var/lib/postgresql`, following the [official image layout](https://hub.docker.com/_/postgres). The database has no published host port. The console/API bind only to loopback. A Compose volume preserves synthetic refunds and approvals across restarts; do not expect an already-refunded example to reset automatically.

Demo users are `pilot` (Northstar manager / Orbit security reviewer) and `analyst` (viewer). Both use the seed password from `DEMO_PASSWORD`. Passwords are stored as salted PBKDF2 hashes. Changing the environment after seeding does not change an existing user's password; rotate it through a reviewed operator procedure or start a new disposable database. Do not delete a volume containing valuable data.

## Native development
Python 3.13 and Node 24 are the validated runtimes. SQLite is optional for a fast offline start:

```bash
cp .env.example .env
# Edit credentials before continuing.
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
alembic upgrade head
python -m backend.db.seed
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd apps/web
npm ci
npm run dev
```

The console calls `http://localhost:8000` unless `NEXT_PUBLIC_API_URL` is set at build time. For native PostgreSQL, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE` before migrations and startup. URL-encode credentials where required. Use PostgreSQL rather than SQLite for concurrency testing.

## Environment variables
| Variable | Purpose | Exposure |
|---|---|---|
| `JWT_SECRET` | Session signing; minimum 32 random characters | Backend secret |
| `DEMO_PASSWORD` | Initial password for seeded demo accounts; minimum 12 characters | Backend secret |
| `DATABASE_URL` | SQLAlchemy SQLite or PostgreSQL URL; Compose overrides to its internal DB | Backend secret |
| `POSTGRES_PASSWORD` | Local Compose database password; use URL-safe characters | Local/DB secret |
| `CORS_ORIGINS` | Comma-separated, exact browser origins | Backend |
| `AGENT_MODE` | `offline` (default) or `live` | Backend |
| `OPENAI_API_KEY` | Required only for live recommendations and live evaluation | Backend secret |
| `OPENAI_MODEL` | Structured-output capable model; configurable default `gpt-4.1-mini` | Backend |
| `INPUT_COST_PER_MILLION`, `OUTPUT_COST_PER_MILLION` | Operator-configured USD model rates; zero means unconfigured | Backend |
| `TOKEN_TTL_MINUTES` | Session lifetime, default 60 | Backend |
| `NEXT_PUBLIC_API_URL` | Public API origin embedded into the frontend build | Public; never put secrets here |
| `TEST_DATABASE_URL` | Optional disposable PostgreSQL test database; fixtures drop tables | Test only |

Live mode uses the [OpenAI Responses API's structured output helper](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), one read-only context tool and a strict Pydantic recommendation schema. Model access and API billing must be configured independently. No API key is necessary for the offline demo. A provider timeout, refusal or invalid response escalates to human review.

## Verification commands
```bash
ruff check backend apps/api tests
pytest -q
python -m backend.evaluations.runner
alembic check
cd apps/web
npm run build
npm run typecheck
```

Set `TEST_DATABASE_URL` to a disposable database for real row-lock tests. The fixtures own and drop that database's application tables. Never point it at shared, production or valuable data. Browser verification instructions are in `DEMO_SCRIPT.md`.

For a standalone production frontend outside Docker, run `npm run build`, copy `.next/static` into `.next/standalone/.next/static`, then run `HOSTNAME=0.0.0.0 node .next/standalone/server.js` from `apps/web`. The Dockerfile performs this packaging automatically.

## Cloud deployment plan (not deployed)
1. Provision managed PostgreSQL with encrypted transport, backups and separate application/migration roles. Set `DATABASE_URL` using the `postgresql+psycopg` scheme and provider TLS parameters.
2. Configure Render for the repository's `apps/api/Dockerfile` with repository root as context. Set secrets through its environment UI, exact HTTPS `CORS_ORIGINS`, and `/health` as the health path. The container honors `PORT`.
3. Run migration and seed as a single controlled release operation. For a real system, replace demo seeding and authentication first; do not run concurrent migration jobs.
4. Deploy `apps/web` to Vercel with its Next.js preset and `NEXT_PUBLIC_API_URL` set to the API's HTTPS origin. Rebuild whenever the API origin changes.
5. Verify login, switching, both workflows and refusal/failure handling over HTTPS. Check that no secrets appear in frontend assets.
6. Add OIDC, shared rate limiting, retention, least-privilege DB roles and observability export before accepting real data. Use an outbox and provider idempotency before external payments or other side effects.

No public deployment or video is claimed. The local verification record is in `EVALUATION_REPORT.md`.
