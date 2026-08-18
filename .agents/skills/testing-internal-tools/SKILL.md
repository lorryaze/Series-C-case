---
name: testing-internal-tools
description: How to bring up and end-to-end test the internal-tools platform (KYC queue, Refunds dashboard, Feature Flags) in this repo — services, logins, RBAC expectations, and the fastest ways to verify mutations, validation and audit trails.
---

# Testing the internal-tools platform

## Bring the stack up
- `docker compose up --build -d` from the repo root. Frontend `http://localhost:3000` (nginx proxies `/api` and `/docs`), backend `http://localhost:8000`.
- After a machine restart nothing is running — `docker compose ps` first; if port 8000 is held by a stray uvicorn, kill it.
- Manual alternative: `backend/.venv/bin/alembic upgrade head && backend/.venv/bin/python seed_data.py && backend/.venv/bin/uvicorn app.main:app --port 8000`, plus `cd frontend && npm install && npm run dev`.
- Data is re-seeded to 60 KYC cases / 120 refunds / 16 flags. Counts drift once you perform mutations, so record baseline card values before acting rather than trusting a fixed number.

## Logins
`admin@fintech.com`, `reviewer@fintech.com`, `viewer@fintech.com`, all with password `demo123`.
The login page has one-click demo-account buttons — click the account, then retype the password field (clicking the account can leave a stale password). Field coordinates shift when an error banner appears, so re-screenshot before clicking Sign in.

## Role expectations (verify both UI and API)
- admin: only role that may mutate feature flags.
- reviewer: KYC + refund decisions; feature flags read-only with an amber "changes require an admin account" notice and a disabled `New flag` button.
- viewer: read-only everywhere — no KYC row checkboxes, detail drawers show only a `Close` footer, flag toggles/sliders rendered disabled.
- Hidden buttons are not proof. Verify server-side too, e.g.
  `TOKEN=$(curl -s localhost:8000/api/auth/login -H 'content-type: application/json' -d '{"email":"viewer@fintech.com","password":"demo123"}' | jq -r .access_token)`
  then `curl -i -X POST localhost:8000/api/kyc/reviews/1/approve -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason":"x"}'` → 403 `permission_denied` with required/actual roles in the body. Same for `POST /api/feature-flags/1/toggle` as reviewer.
- Collection endpoints are `/api/kyc/reviews`, `/api/refunds`, `/api/refunds/summary`, `/api/refunds/trend`, `/api/feature-flags`. There is no `/api/kyc/stats`; `/api/refunds/stats` is parsed as an ID and 422s.

## Fast, high-signal checks
- Decision validation: every KYC/refund action requires a reason ≥3 chars; empty or `ab` must produce an inline red message and no status change / no audit entry.
- Already-decided guard: re-deciding a decided refund returns 409 and an inline "… is already rejected" message — expected, not a bug.
- Duplicate flag name returns 409 with an inline error in the modal; the `Create flag` button stays disabled until both name and description are ≥3 chars.
- Rollout slider persistence is best verified with F5 plus the flag's History modal (History shows `Created`, `Toggled … enabled False → True`, `Updated … rollout_percentage 100 → 50` with actor email + timestamp).
- Known cosmetic gap to re-check: the flag list "Last modified" column may not update after environment toggle / rollout changes even though History records them.
- Reading the annotated DOM (`read_dom` or the HTML returned with screenshots) is much faster than pixel-inspecting counts, `disabled` attributes and audit-log text.

## Logs
`docker compose logs backend | grep -E '" (4|5)[0-9][0-9] '` — intentional codes are 401 (bad login), 403 (RBAC), 409 (duplicate flag / already-decided). Any 5xx is a real bug. Browser console normally shows only React Router `v7_startTransition` / `v7_relativeSplatPath` future-flag warnings.

## Devin Secrets Needed
None — all credentials are seeded demo accounts.
