# Internal Tools Platform

A production-shaped replacement for the three internal tools this company currently runs on
Microsoft Power Apps — **KYC Review Queue**, **Refunds Dashboard** and **Feature Flags Admin
Panel** — built on one shared foundation so the marginal cost of tool #4 through #13 is a page
and a service, not a new application.

Everything the three tools have in common (auth, RBAC, audit trail, pagination, filtering,
error envelopes, request logging, layout shell, tables, modals, data fetching) lives in shared
layers. Each tool contributes only its own domain model, service, router and page.

| Tool | Backend | Frontend | Tool-specific code |
| --- | --- | --- | --- |
| KYC Review Queue | `routers/kyc.py`, `services/kyc_service.py`, `repositories/kyc_repository.py` | `pages/KycQueuePage.tsx` | ~3 files + components |
| Refunds Dashboard | `routers/refunds.py`, `services/refund_service.py`, `repositories/refund_repository.py` | `pages/RefundsPage.tsx` | ~3 files + components |
| Feature Flags | `routers/feature_flags.py`, `services/feature_flag_service.py`, `repositories/feature_flag_repository.py` | `pages/FeatureFlagsPage.tsx` | ~3 files + components |

## Architecture

```text
┌──────────────────────────────── Browser (:3000) ────────────────────────────────┐
│  React 18 + TypeScript + Vite + Tailwind                                        │
│                                                                                 │
│  AppShell (Sidebar · Header · AuthContext · ErrorBoundary)                       │
│    ├── /kyc            KycQueuePage      ─┐                                     │
│    ├── /refunds        RefundsPage        ├── shared: Table, Modal, Card,        │
│    └── /feature-flags  FeatureFlagsPage  ─┘   Badge, FilterBar, AuditTrail       │
│                                                                                 │
│  hooks/ (TanStack Query)  →  services/ (typed API client, JWT bearer)            │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │  /api  (nginx proxy in Docker,
                                       │         Vite proxy in dev)
┌──────────────────────────────────────▼──────────────────────────────────────────┐
│  FastAPI (:8000)                                                                │
│                                                                                 │
│  middleware/     request id + logging · JWT auth · structured error envelope     │
│  routers/        auth · kyc · refunds · feature_flags        (HTTP only)         │
│  services/       business rules, state machines, audit writes (no HTTP, no SQL)   │
│  repositories/   BaseRepository[Model] + per-domain queries   (all SQL)          │
│  factories/      domain object construction, references, slugs                   │
│  models/         SQLAlchemy 2 mapped classes · schemas/ Pydantic v2 contracts     │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │  SQLAlchemy 2 · Alembic
                                 ┌─────▼─────┐
                                 │  SQLite   │   audit_logs is append-only and
                                 └───────────┘   shared by all three tools
```

Layers only ever call downwards: routers → services → repositories → models. Cross-cutting
behaviour is injected with `Depends()` (`get_db`, `CurrentUser`, `ReviewerUser`, `AdminUser`).

## Run with Docker

```bash
docker compose up --build
```

- Frontend: <http://localhost:3000>
- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs> (also proxied at <http://localhost:3000/docs>)

The backend container runs migrations and seeds the demo dataset on first boot; the SQLite file
lives in a named volume, so restarts keep your changes.

## Run without Docker

Backend (Python 3.11+):

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python seed_data.py                     # re-runnable; wipes and reseeds demo rows
uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev                             # http://localhost:3000, /api proxied to :8000
```

Quality gates:

```bash
cd backend  && pytest && ruff check . && mypy app tests
cd frontend && npm run typecheck && npm run lint && npm run build
```

## Demo credentials

Password for all accounts: `demo123`

| Email | Role | Can do |
| --- | --- | --- |
| `admin@fintech.com` | admin | everything, including feature flags and user creation |
| `reviewer@fintech.com` | reviewer | approve/reject/escalate KYC and refunds, assign reviewers |
| `viewer@fintech.com` | viewer | read-only across all three tools |

RBAC is enforced server-side in FastAPI dependencies; the UI merely hides what the API would
reject with `403`.

## Seeded dataset

`backend/seed_data.py` is deterministic and idempotent: 4 users, 60 KYC cases across all five
statuses with documents/notes/audit history, 120 refunds ($5–$5,000) across four reason
categories spanning the last 90 days, and 16 feature flags with per-environment state.

## API documentation

All endpoints are described with summaries, descriptions and response models at
<http://localhost:8000/docs> (ReDoc at `/redoc`, schema at `/openapi.json`).

## Audit trail

Every mutation in every tool writes one `audit_logs` row through the shared `AuditService`:
entity type, entity id, action, field, previous value, new value, reason, actor and timestamp.
The same `AuditTrail` component renders it in the KYC case drawer, the refund approval chain and
the feature flag changelog.

## Screenshots

_Placeholder — add captures of the KYC queue, refunds dashboard and feature flags panel here._

| View | Screenshot |
| --- | --- |
| KYC Review Queue | _TBD_ |
| Refunds Dashboard | _TBD_ |
| Feature Flags | _TBD_ |
