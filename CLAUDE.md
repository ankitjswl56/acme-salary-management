# CLAUDE.md — Project Instructions

This file is read automatically by Claude Code at the start of every session in
this repo. It is the single source of truth for scope, architecture decisions,
and process discipline for this project. Follow it exactly — do not silently
deviate from stack, schema, or scope decisions below. If something here seems
wrong or you want to propose a change, surface it explicitly for discussion
rather than quietly doing something different.

## What this project is

Employee salary management software for a 10,000-employee, multi-country
organization (ACME), for the HR Manager persona (plus Admin and Executive
Viewer roles — see RBAC below). This is a take-home engineering assessment for
Incubyte (Software Craftsperson / Python / AI role). Full context, scope, and
reasoning live in `docs/requirements.md` — read it before starting work if you
haven't already loaded it this session.

The brief explicitly grades: engineering judgment, product thinking, clean
architecture, meaningful tests, **intentional and well-documented AI tool use**,
and **commit history that shows incremental evolution**. Every instruction below
exists to satisfy one of these grading criteria — treat them as real
requirements, not nice-to-haves.

## Locked tech stack — do not deviate

- **Backend**: Python, FastAPI, SQLite, SQLModel (or SQLAlchemy) as ORM
- **Frontend**: React + Vite (explicitly not Next.js — no SSR/SEO need for an
  internal authenticated tool; see requirements doc for reasoning)
- **Auth**: JWT-based, custom (not SSO/OAuth — out of scope, see requirements
  doc)
- **Containerization**: Docker Compose (backend + frontend services; SQLite as
  a file on a mounted volume, no separate DB container)
- **Stretch-only LLM integration**: OpenRouter, **explicit free-tier model IDs
  only** (e.g. `meta-llama/llama-3.1-8b-instruct:free`) — never use
  auto-routing or an unpinned model. See "OpenRouter guardrails" section below
  before writing any code that calls it.

## Data model — locked decisions

```
User
  id, email, hashed_password, role (admin | hr_manager | executive_viewer)

Employee
  id, name, email, country, department, role, gender (optional,
  non-binary-inclusive: male | female | other | prefer_not_to_say),
  hire_date, status (active | inactive)

SalaryRecord
  id, employee_id (FK), amount, currency, amount_usd_snapshot,
  fx_rate_to_usd, effective_date, change_type
  (hire | raise | promotion | correction | cola), created_at
```

Key rules — implement exactly this way, do not "simplify" to a mutable
current-salary field:

- **Append-only history**: never UPDATE a SalaryRecord's amount. Every change
  (raise, promotion, correction) is a new row. This is the audit trail.
- **"Current salary" is derived, not stored**: the latest SalaryRecord per
  employee where `effective_date <= today`. Future-dated records (e.g. a raise
  scheduled for next quarter) must NOT be treated as current until their date
  arrives — write this as an explicit, tested query condition, not an
  afterthought.
- **Currency correctness**: `amount_usd_snapshot` and `fx_rate_to_usd` are
  captured at record-creation time and never recalculated later. Historical
  figures must stay accurate regardless of future FX movement. Never do a
  live/runtime FX lookup for historical records.
- **Gender field privacy rule**: headcount/ratio by gender (a count) is always
  safe to display at any group size. Average salary by gender within a
  department/role (a number derived from individuals' pay) must only be shown
  when the group size meets a minimum threshold (use 5 unless told otherwise)
  — smaller groups risk indirectly exposing one person's salary. Implement
  this suppression in the query layer, not just the frontend.

## RBAC — three roles, real but lightweight

- **admin**: full read/write on employee & salary data, plus user management
- **hr_manager**: full read/write on employee & salary data, no user management
- **executive_viewer**: read-only, aggregate analytics endpoints only — must
  NOT be able to read individual employee records, only dashboard/aggregate
  data

Implementation: JWT issued on login (email/password, bcrypt-hashed passwords),
decoded via a FastAPI dependency, role-gated via a `require_role([...])`
dependency on each protected route. Seed 3 demo users (one per role, same
demo password) as part of the seed script so the reviewer can log in as each
and see access differences directly. Do not build password reset, email
verification, refresh-token rotation, or SSO — explicitly out of scope.

## Seed script — 10,000 employees, must be realistic and correlated

Do not generate salary independently at random. Build small reference tables
first (country → salary multiplier tier, department/role level → base salary
band, country → currency + fixed FX-to-USD rate), then derive each employee's
salary from these tables with some randomized variance (e.g. ±15%) on top —
so aggregate dashboard numbers look plausible and internally consistent
(e.g. Engineering pays more than Support; US pays more than lower-cost-tier
countries), not like noise.

For ~15-20% of employees, generate a short realistic salary history (hire →
raise/promotion → maybe another change) with sensible dates and change_types,
so the "recent changes" feed and payroll-trend-over-time chart have real
content to show — not 10,000 flat single-record employees.

Use a fixed random seed so the dataset is reproducible run to run. Bulk-insert
(not one-row-at-a-time ORM adds) for performance at 10k scale — note this as a
deliberate performance decision in `docs/design-notes.md` if it comes up.

## Analytics — the 8 fixed dashboard views

1. Avg & median salary by country (USD-normalized)
2. Avg & median salary by department
3. Headcount + total payroll by country
4. Org-wide salary distribution (histogram/bands)
5. Gender ratio by department/org-wide (headcount-based, always shown)
6. Avg salary by gender within role/department (min-group-size gated, see
   above)
7. Recent salary changes feed (last N months, filterable by change_type)
8. Payroll cost trend over time (by quarter)

Build these as real, tested backend query functions first — the frontend
dashboard just renders their output. These same functions are also what the
stretch NL-query feature calls into (see below) — do not duplicate logic.

## Stretch feature — natural-language analytics query (build only if core is done)

Scope: **read-only, analytics only. No write path, ever.** HR types a question
in plain English; an LLM call maps it to one of the 8 predefined query
functions above (function-calling / structured-output style — the model
selects a function name + typed parameters from a fixed list), the backend
runs the actual function, and the result is returned. The LLM never generates
SQL, never touches the database directly, and has no ability to trigger a
write (bulk raises, new employees, edits) — those remain deliberate,
human-confirmed structured UI forms, on purpose: compensation changes warrant
an explicit human decision point, not natural-language interpretation. State
this reasoning in `docs/design-notes.md` if this feature is built.

### OpenRouter guardrails — required if this feature is built
- Hardcode an allowlist of permitted model IDs (free-tier only, e.g.
  `meta-llama/llama-3.1-8b-instruct:free`) in backend config. Reject/refuse to
  call any model not in this list — never pass through a user- or
  auto-selected model. This exists because free-vs-paid model routing has
  silently caused negative account balances before; the allowlist is a hard
  code-level guard against that recurring.
- If the model's function-selection output doesn't match one of the 8
  predefined functions, return a polite "I can only answer questions about
  salary data" — do not let the model answer freeform outside that scope.
- Keep the OpenRouter API key in `.env`, never committed. Document the
  required env var in `README.md`.

## Testing philosophy

Prioritize tests on logic with real correctness risk — this is where bugs
actually hide and where "meaningful tests" (as the brief asks for) matters:
- Current-salary resolution (including the future-dated exclusion case)
- Currency normalization math
- All 8 aggregation queries, especially the min-group-size suppression logic
- RBAC permission checks (each role can/cannot access what it should)

Do not pad coverage with trivial "does this endpoint return 200" tests at the
expense of the above. Tests must be fast and deterministic — no reliance on
real time (`datetime.now()` directly) without a way to inject/mock it, no
network calls, no flaky ordering.

## Commit discipline — required by the assessment brief, non-negotiable

Commit after each meaningfully complete unit of work, not in large batches.
Follow the phase plan below as natural commit checkpoints. Write commit
messages that explain **why**, not just what changed, where the reasoning
isn't obvious from the diff alone. Never squash the incremental history before
submission — the brief explicitly wants to see the evolution, not a single
clean final commit.

## Mid-phase checkpoints (important)

Do not silently complete an entire phase (or a large chunk of one) before
raising commits. Instead, pause and explicitly suggest a commit — with a
proposed message — at each of these natural breakpoints, even within a
single phase:

- After a new data model / schema piece is added and passes a basic sanity
  check
- After a new endpoint (or small group of closely related endpoints) is
  implemented and its tests pass
- After a frontend view/component is functional and visually verified
- Before starting a materially different sub-task within the same phase
  (e.g. "models are done, now starting the seed script logic" — pause first)
- Any time you're about to touch 5+ files in one sitting

When you reach one of these points, stop and say something like:
"This looks like a good commit checkpoint — [1-sentence summary]. Suggested
commit message: '...'. Want me to commit this before continuing?" Then wait
for confirmation before proceeding to the next sub-task. Do not batch
multiple unrelated pieces of work into one commit just because they happened
in the same session.

## Required artifacts — maintain these throughout, not just at the end

- `docs/requirements.md` — already drafted; do not rewrite, only reference
- `docs/design-notes.md` — append trade-off explanations and design decisions
  as they come up during building (not reconstructed from memory at the end)
- `docs/ai-log.md` — append a curated entry (not a full transcript) whenever a
  meaningful AI-assisted decision is made: what was asked, what was produced,
  what was accepted as-is vs. corrected and why. Skip routine/trivial
  exchanges. Aim for a handful of substantive entries, not exhaustive logging.
- `README.md` — keep current: how to run `docker compose up`, how to run the
  seed script, how to run tests, required env vars, demo login credentials
  for each role

## Build plan — phases (use as commit checkpoints)

0. Scaffold: repo structure, empty FastAPI + Vite apps wired via Docker
   Compose, `.gitignore`, `.env.example`
1. Data models (Employee, SalaryRecord, User) + DB init
2. Seed script — 10k realistic/correlated employees + demo users
3. Core CRUD endpoints (employees, salary records) + tests
4. Analytics endpoints (8 views) + tests
5. Auth/RBAC (login, JWT, role gating)
6. Frontend — employee list/detail/forms, bulk raise, CSV import
7. Frontend — analytics dashboard (8 views, role-gated)
8. Stretch — NL query via OpenRouter (only if 0-7 solid, with guardrails above)
9. Polish — README, docs finalized, fresh `docker compose down -v && up`
   validation, demo video

Do not jump ahead of this order (e.g. don't build frontend polish before core
backend correctness is tested) — the phases are sequenced so that each one
depends on a solid, tested version of the last.
