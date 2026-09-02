# Salary Management Software — Requirements Document

## Goal
Replace ACME's Excel-based salary tracking with a web-based system that lets the HR
Manager (and, in a read-only capacity, senior leadership) manage salary data for
10,000 employees across multiple countries, and — critically — **answer questions
about how the org pays people**, not just store the numbers.

The core insight driving scope: a spreadsheet can hold data, but it can't easily
answer "what's our average pay in Germany," track *why* someone's salary changed,
or stay currency-correct over time. This system is designed around those needs
from the data model up, not bolted on as an afterthought.

## User Personas
- **Admin** (owner/CTO-level) — full read/write access, plus user/role
  management (creating HR accounts, etc.). The "keys to the system" role.
- **HR Manager** — primary day-to-day user. Full read/write access to employee
  and salary data: add employees, record salary changes, search/filter records,
  view all analytics. No user-management access.
- **Executive Viewer** (CEO/CTO/etc. who just wants visibility) — read-only
  access to aggregate analytics/dashboard views only — not individual employee
  salary records. Reflects a realistic sensitivity boundary: leadership often
  wants org-level insight without line-item access to any one person's pay.

## In Scope
- **Employee records**: name, email, country, department, role, gender (optional,
  non-binary-inclusive), hire date, employment status (active/inactive).
- **Salary history, not overwritten state**: every hire, raise, promotion, or
  correction is a new append-only record with an effective date and a reason
  (`change_type`). Current salary = latest record with `effective_date <= today`
  (future-dated changes, e.g. a raise scheduled for next quarter, are supported
  and correctly excluded from "current" until they take effect).
- **Multi-currency correctness**: each salary record stores its native currency
  amount alongside a USD-normalized snapshot and the FX rate used at that time —
  so historical figures stay accurate regardless of how exchange rates move later.
- **Search & filter** employees by country, department, role, status.
- **Bulk salary updates** (e.g. apply a % raise across a country/department) —
  a realistic HR operation, cheap to support given the append-only schema.
- **CSV import** for onboarding batches of employees — directly mirrors the
  brief's framing of moving *off* Excel.
- **Role-based access control**: Admin (full + user management) vs. HR Manager
  (full data access) vs. Executive Viewer (read-only, aggregates only). Login is
  simplified/mocked — see Out of Scope.
- **Analytics dashboard** — a fixed set of pre-built views answering the most
  common HR questions directly, rather than requiring HR to build their own
  reports:
  1. Average & median salary by country (USD-normalized)
  2. Average & median salary by department
  3. Headcount and total payroll by country
  4. Org-wide salary distribution (bands/histogram)
  5. Gender ratio by department/org-wide (headcount-based — always shown, no
     privacy risk since it's a count, not a salary figure)
  6. Average salary by gender within role/department — shown only where group
     size meets a minimum threshold, to avoid indirectly exposing an individual's
     salary in small groups
  7. Recent salary changes feed (raises/promotions in the last N months) —
     useful for performance-review and audit purposes
  8. Payroll cost trend over time (by quarter) — supports budget planning
- **Basic validation**: non-negative salaries, currency restricted to a supported
  list, sensible date bounds.
- **Seed script**: 10,000 employees with *realistic* correlated data — salary
  ranges vary sensibly by country and by department/role, not independently
  randomized — so the dashboard reflects plausible, checkable numbers rather
  than noise.
- **Deployment readiness**: Docker Compose as the primary, guaranteed-to-run
  artifact (avoids reliance on a free-tier host being awake at review time);
  optional live deploy as a bonus.
- **Audit trail via append-only history**: because salary records are never
  overwritten, the system inherently retains a full change history — a
  meaningful improvement over Excel's overwrite-and-lose-history failure mode,
  even without a dedicated backup feature (see Out of Scope).
- **Stretch feature — natural-language analytics query**: an LLM-backed input
  (e.g. "what's our average salary in Germany for engineers?") that maps the
  question to one of the pre-defined, parameterized analytics functions already
  powering the dashboard, then returns the answer in natural language. The LLM
  is deliberately *not* given free rein to generate SQL against the database —
  it selects from a constrained set of safe query functions — to avoid
  prompt-injection / arbitrary-query risk. Uses OpenRouter so the project isn't
  locked to a single paid provider. Built only if core scope is complete first.

## Deliberately Out of Scope (and why)
- **Enterprise SSO/full identity infrastructure** — role-based access control is
  implemented, but real SSO (Okta/SAML) is infrastructure, not the product
  problem this exercise is about.
- **Live/real-time FX rate lookups** — rates are snapshotted at record-creation
  time for historical accuracy; a live FX feed is an integration detail that
  doesn't change the core design.
- **Payroll execution / tax compliance** — this is a salary *management* system,
  not a payroll *processing* engine. Calculating net pay, tax withholding, or
  actually disbursing payments is a materially different (and heavily
  regulated) problem.
- **Multi-user concurrent write conflict handling** (optimistic locking, etc.) —
  the brief specifies a single HR Manager persona; this is a reasonable scope
  cut for that assumption, stated explicitly rather than silently ignored.
- **Employee self-service portal / notifications** — out of scope per the given
  persona (HR Manager and leadership only, not individual employees).
- **Performance review content, leave/attendance tracking** — adjacent HR
  domains, not salary management.
- **Data backup/DR** — not implemented. A local copy of the SQLite file on the
  same disk/host does not meet the actual bar for "backup" (it doesn't protect
  against disk or host loss) and would only create a false sense of safety. A
  real implementation would sync the DB (or Postgres WAL) to separate storage
  (e.g. S3, or a managed DB provider's automated snapshotting) on a schedule.
  This is infrastructure appropriate to a production deployment, not to this
  exercise's scope.

## Technical Approach (summary — see architecture notes for detail)
- **Backend**: Python (FastAPI) + SQLite, SQLAlchemy/SQLModel ORM
- **Frontend**: React (Vite) — Next.js's core advantages (SEO, SSR) don't apply
  to an internal, authenticated tool, so the simpler tool is the better fit
- **Containerization**: Docker Compose for one-command setup
- **LLM (stretch feature only)**: OpenRouter — provider-agnostic API access,
  avoids locking the demo to one paid vendor, and has low/no-cost model options
  suitable for a demo-scale project
- **Testing**: unit tests focused on the logic with real risk of bugs — current-
  salary resolution, currency normalization, and aggregation queries — rather
  than padding coverage on simple CRUD endpoints
