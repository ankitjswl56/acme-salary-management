# Salary Management Software — Design Notes

## Employee list: URL is the source of truth for filters/pagination

`EmployeesPage.tsx` reads search/country/department/status/page/pageSize
from `useSearchParams()` rather than plain component state. Two review
requests drove this together rather than separately: filters should
survive a browser refresh, and there should be an explicit way to clear
them instead of relying on a refresh as an ad-hoc "reset." Encoding state
in the URL solves both at once - a refresh re-reads the same URL, and
Reset is just `setSearchParams({})`. It also happens to make the current
filtered view a shareable/bookmarkable link, which wasn't asked for but
falls out of the same mechanism for free.

Search text stays in local state and is only pushed into the URL once
the existing debounce settles (`replace: true`, not `push`) - otherwise
every keystroke would both spam browser history and fire a fetch.

Default sort is `Employee.id DESC` (most recently added first).
`Employee` has no `created_at` column - CLAUDE.md's schema is locked and
doesn't include one - but `id` is sequential on insert in this app's
usage pattern (no deletes/reinserts), so it's a reliable proxy without a
schema change.

## CSV import reuses create_employee()/create_salary_record() per row

`import_employees_csv()` (app/services/csv_import.py) doesn't reimplement
employee/salary validation — each row calls the exact same
`create_employee()` and `create_salary_record()` functions the
single-employee forms use, so a CSV row is held to identical rules
(duplicate email, currency allowlist, effective_date >= hire_date, valid
enum values) and can't silently drift from them as a second, parallel
implementation would risk.

A row optionally includes `amount`/`currency`; if both are present, an
initial "hire" `SalaryRecord` is created alongside the `Employee`
(`effective_date = hire_date`) — otherwise every CSV-onboarded employee
would start with no salary on record, the same gap the single-employee
create form has (deliberately: creating an employee and recording their
pay are separate concerns there), just multiplied across an entire batch,
which is a real usability problem specifically for bulk onboarding.

**Partial success, two different kinds.** A row that fails to produce an
*employee* at all (bad required field, duplicate email) is a real error -
skipped and counted in `errors`. A row whose employee was created fine but
whose salary columns failed validation (e.g. unsupported currency) is
different: the employee import itself still succeeded, so it's reported
separately in `salary_warnings` rather than as a failure. This distinction
matters because `create_employee()` and `create_salary_record()` each
commit independently (they're designed as standalone single-operation
functions, reused here rather than rewritten) - by the time a salary
error surfaces, the employee row is already durably committed, so there's
nothing to roll back even if the two were reported identically.

Reads the uploaded file as `utf-8-sig` rather than plain `utf-8`: Excel
commonly writes a UTF-8 BOM at the start of a CSV it exports, and decoding
that with plain `utf-8` leaves a stray character prefixed to the first
column's header, silently breaking the "missing required column" check.

## Bulk raise: local currency, restricted change_type, partial success

`apply_bulk_raise()` (app/services/bulk.py) applies a % change to every
active employee matching an optional country/department filter, in one HR
action. A few decisions worth recording:

- **Always active-only, not a status filter.** There's no `status`
  parameter at all - not defaulted to active and overridable, genuinely
  not offered as a choice. A raise for someone who's already left the
  company (`status = inactive` means no longer employed) isn't a real
  scenario, so it isn't presented as one; a stray `"status"` key in the
  request body is silently ignored by pydantic rather than accepted.
  Flagged by the user reviewing the form: "why would HR want to raise
  someone who's not active?"
- **Applied to local currency, not USD.** The window-function query
  fetches each employee's current `amount`/`currency` (not
  `amount_usd_snapshot`), so a GBP earner's raise multiplies their GBP
  figure — reusing `normalize_to_usd()` afterward for the new USD
  snapshot, same as every other SalaryRecord write. Applying the
  percentage to a USD-converted figure and converting back would drift
  from what the employee's contract is actually denominated in.
- **Restricted to change_type raise/cola.** Promotion is inherently
  individual (paired with a specific new role - see the new_role note
  below); correction/hire are one-off single-employee fixes. Neither
  makes sense applied identically across a whole department.
- **Percentage must be strictly positive - no bulk pay cuts.** Initially
  allowed any percentage > -100 (framed as "supports a pay cut too"), but
  that's a real UX problem: a negative percentage inserts a SalaryRecord
  with change_type "raise" whose amount is actually *lower* than the
  prior one, reading as self-contradictory in the salary history table.
  Flagged by the user reviewing the form. `docs/requirements.md` only
  ever asks for "apply a % raise" - a bulk pay-cut feature, if ever
  needed, deserves its own change_type concept (`ChangeType` is locked
  and has no "cut" value), not a sign flip on this endpoint.
- **Partial success, not all-or-nothing.** An employee with no current
  salary record yet, or one whose (possibly since-corrected) hire_date
  now postdates the raise's effective_date, is skipped rather than
  aborting the entire batch - the response reports
  matched/applied/skipped_* counts so HR can see exactly what happened,
  rather than a raise for 998 of 1000 people failing outright because of
  2 edge cases.
- **Confirmed client-side before submitting**, since it's the app's first
  action that writes to many employees in one request - a plain
  `window.confirm()` naming the scope (no separate dry-run/preview
  endpoint; the confirm text states the filters, not an exact matched
  count).

## "hire" can only be an employee's first SalaryRecord

Flagged by the user: the add-salary-record form offered "Hire" as a
change_type option even for an employee who already had salary history,
which doesn't make sense - you don't re-hire someone who's already
employed. `create_salary_record()` now rejects a "hire" record if the
employee already has *any* SalaryRecord (of any change_type, not just an
existing hire) - enforced in the service layer, not just hidden in the
UI, so a direct API call can't create a nonsensical second hire either.
The frontend also drops "Hire" from the dropdown once history exists, and
defaults change_type to "hire" only when there's no history yet.

The seed script is unaffected: it bulk-inserts SalaryRecord rows directly
rather than going through create_salary_record(), and never generates a
second hire per employee in the first place.

## Promotions update Employee.role atomically with the SalaryRecord

`raise` vs `promotion` in `change_type` wasn't documented anywhere beyond
the enum name, and the two were functionally identical: recording either
just inserted a `SalaryRecord` and never touched `Employee.role`. Surfaced
when asked directly "what's the difference" — the honest answer at the
time was "only the label."

The intended distinction: `raise` is a pay change with no role/level
change (merit increase, market adjustment); `promotion` is a pay change
tied to a role/level change. Decided to make that real rather than
document-only: `SalaryRecordCreate.new_role` (optional) updates
`Employee.role` in the same commit as the `SalaryRecord` when set (see
`create_salary_record()`), so a promotion's title change can't be saved
and then forgotten as a separate edit. Not restricted to
`change_type == promotion` at the schema/service level — the frontend
only surfaces the "new role" field for promotions, but the backend stays
generically usable (e.g. a correction that also happens to fix a
wrongly-recorded title).

## This system doesn't track monthly payroll disbursement

Came up when asked whether "salary updated each month" is a feature. It
isn't, and per `docs/requirements.md`'s explicit out-of-scope list:
payroll *execution* (calculating net pay, disbursing payments) is a
different, heavily-regulated problem from salary *management*. A
`SalaryRecord` is only written when compensation actually changes (hire,
raise, promotion, correction, cola) — never a recurring monthly entry.
"Current salary" is the annual/base rate implied by the latest change,
not a payment ledger.

Worth flagging so it doesn't read as a contradiction: `payroll-trend`
(quarterly payroll cost analytics) is an *estimate* of compensation run
rate — it sums each active employee's current annual salary at each
quarter-end — not a record of money actually disbursed.

## Payroll trend by quarter ignores Employee.status entirely

`payroll_trend_by_quarter()` is the one analytics view that doesn't filter
by `active_only` at all (`get_current_salary_snapshots(..., active_only=False)`).
`Employee.status` is a point-in-time flag ("is this person active *right
now*"), not a tracked history — there's no termination date in the schema.
For a past quarter, "were they active back then" isn't a question the data
can answer, so filtering a historical trend by *current* status would just
be wrong (e.g. it would silently drop payroll for a Q1 2024 employee who
left in 2025). Instead, an employee counts toward a quarter if they had any
applicable SalaryRecord by that quarter's end — which is also naturally
capped at `min(quarter_end, as_of)` so an already-scheduled future raise
can't inflate the current, still-in-progress quarter before it takes
effect.

## Analytics: current-salary-per-employee via SQL window function, grouping/median in Python

All "current state" analytics views (1-6) share one building block —
`get_current_salary_snapshots()` in `app/services/analytics.py` — which
resolves each employee's *current* SalaryRecord (latest with
`effective_date <= as_of`) using a `ROW_NUMBER() OVER (PARTITION BY
employee_id ORDER BY effective_date DESC, id DESC)` window query, joined
back to Employee. This is the same "current salary" rule as the CRUD detail
endpoint and the standalone `get_current_salary_record()` service, just
resolved for every employee in one query instead of one row at a time —
necessary to avoid N+1 queries at 10k-employee scale.

Grouping and median are then done in Python (`statistics.median`,
dict-based groupby) rather than pushed further into SQL. SQLite has no
native `MEDIAN`/percentile aggregate, and a portable one requires either a
second window-function pass or DB-specific extensions. At this data scale
(10k employees, one row each after the join) an in-Python groupby is
simpler to read, test, and keep portable if the DB is ever swapped —
traded a small amount of query-pushdown performance for that simplicity,
which is the right call at this scale.

## No hard delete for Employee

The Employee CRUD API (Phase 3) intentionally has no `DELETE /employees/{id}`.
Employees are offboarded via `PATCH .../status = inactive`, not row deletion.
Hard-deleting an employee would cascade into deleting or orphaning their
`SalaryRecord` history — directly undermining the append-only audit trail
that's the core value proposition of this system (see CLAUDE.md's data model
section). `status` already models "no longer employed" without destroying
history, so a destructive delete endpoint would be redundant risk with no
real use case.

## Enum columns store `.value`, not `.name` (SQLAlchemy default is the opposite)

SQLAlchemy's `Enum` type persists a Python `Enum` member by its **name** by
default, not its `.value`, unless `values_callable` is supplied. That's a
silent trap the moment a member's name and value diverge — which happens
here: `ChangeType.raise_ = "raise"` (`raise` is a Python keyword, so the
member can't be named `raise`). Without the fix, salary records were being
stored with `change_type = "raise_"` instead of `"raise"`, silently
diverging from the `hire | raise | promotion | correction | cola` contract
in CLAUDE.md — caught by manually inspecting seed output during Phase 2, not
by any test, since the round-trip through `.value` inside the ORM read path
would have masked it in a naive test.

Fixed via a shared `enum_column()` helper (`app/models/enums.py`) that all
four enum-typed columns use, forcing `values_callable=lambda cls: [e.value
for e in cls]`. Applied to all four enum columns for consistency, even
though only `ChangeType` was actually affected — relying on name/value
happening to match for the other three would be fragile.

## Seed script clears tables before inserting

`app/seed/run.py` deletes existing `Employee`/`SalaryRecord` rows before
bulk-inserting fresh ones, rather than appending. This makes re-running the
seed script idempotent and reproducible given the fixed random seed —
running it twice produces the same 10,000 employees, not 20,000. Employee
and SalaryRecord ids are assigned explicitly in Python (not left to SQLite's
autoincrement) so salary records can reference their employee's id directly
in one bulk-insert pass, without a round trip to read back generated ids.

## Bulk insert via SQLAlchemy Core, not ORM `add()`

Employee/SalaryRecord rows are inserted via `Table.insert()` executed with a
list of dicts (`conn.execute(table.insert(), rows)`), which SQLAlchemy
batches via `executemany`. This skips the ORM unit-of-work/identity-map
overhead entirely — necessary at 10k+ rows per CLAUDE.md's explicit
guidance to avoid one-row-at-a-time ORM adds.

## Auto-seed on first startup (`seed_if_empty` in the app lifespan)

The FastAPI lifespan handler calls `seed_if_empty()` right after `init_db()`.
It checks whether the `Employee` table has any rows and, only if it's empty,
runs the same `seed_core_data()` + `seed_demo_users()` the standalone script
uses. If data already exists it returns immediately and touches nothing.

Why: the reviewer should get a fully populated dashboard from a single
`docker compose up`, with no "now run the seed script" step to discover in
the README. The emptiness check makes this safe on *every* container
restart — the seed itself clears-then-inserts, so without the guard a
restart would pointlessly regenerate 10k rows (and reset any manual edits
made while exploring). `python -m app.seed` is still the way to force a
deliberate re-seed during development.

Cost: first boot against an empty volume takes a few extra seconds while
Faker generates the dataset before the API starts serving. That's a
first-run-only cost and an acceptable trade for the zero-step setup.

Testing note: `seed_if_empty(session=...)` takes an optional session so the
"skip when not empty" path can be tested against the in-memory test DB
without hitting the real file-backed engine (`backend/tests/test_seed.py`).

## MUI as the frontend component library (Phase 7 onward only)

Phase 7 (the analytics dashboard) is built with MUI (`@mui/material` +
`@mui/icons-material` + `@mui/x-charts`, Emotion engine). Phases 1–6
(employee list/detail/forms, bulk raise, CSV import) stay on their existing
hand-rolled CSS and are **deliberately not being retrofitted** right now.

`@mui/x-charts` was added (over hand-rolled SVG) because the dashboard has
7 chart views across bar/line/pie forms with axes, legends, tooltips and
responsive resizing — re-implementing that chrome by hand is exactly the
undifferentiated work a library removes, and x-charts shares MUI's theme so
the charts and the surrounding cards/tables stay visually consistent. Each
chart view still ships a plain data table alongside it, so the numbers are
never chart-only.

Why adopt it: the dashboard is the most layout- and component-heavy part of
the app (cards, data tables, tabs, responsive grid, chart chrome). Hand-
rolling all of that to a presentable standard is exactly the kind of
undifferentiated work a mature component library removes, and "clean
architecture / product thinking" is graded here — a consistent, accessible
component system reads better than bespoke CSS of uneven polish.

Why not retrofit Phases 1–6: those views already work and are visually
verified. Porting them would be pure churn against a fixed assessment
deadline with no functional gain. The mixed-styling seam is a conscious,
time-boxed trade — noted here so it's not mistaken for an oversight. If this
were a real product the rest would follow in a fast-follow pass.

## Analytics dashboard — visual design

The 8 views are not 8 identical stacked cards. The design is deliberately
tiered and specific to this being a **global HR compensation tool**, not a
generic dashboard.

**Palette — bond-indigo + brass-gold, not the chart-library default.**
`#3A4E9C` (indigo) for the primary series and single-series bars, `#BE8636`
(brass) for the "median" comparison series and the one accent rule under the
headline figure. Dark mode lightens the indigo to `#7C8EDC`; gold holds.
Rationale: a "statement / ledger" pairing reads as authoritative for money
data, and gold *for the median series and the headline underline* ties the
one non-neutral accent to currency. Deliberately avoided: the x-charts
blue+orange default (reads as a demo), finance-green (P&L / stock-ticker
connotation, wrong for salary), and alarm-red as anything but the reserved
state (`#B23B3B`, used only for a quarter-over-quarter payroll *drop*).
Every series hex was run through the dataviz skill's palette validator —
CVD ΔE ≥ 18 and contrast ≥ 3:1 in both light and dark. (An earlier teal
candidate was dropped: it kept failing the chroma floor at mid-lightness.)

**Depth without elevation.** Cards are a 1px hairline border on a near-white
surface, `border-radius: 8`, and **no drop shadow anywhere** (MuiCard is
themed to force `boxShadow: none`). Separation comes from the border and the
page/card value difference, not a soft-shadow "floating card" look.

**Typography.** System sans throughout (no webfont — internal tool, keeps it
fast). Every salary/payroll figure uses `tabular-nums`. The one bold moment
is the **total-payroll headline figure** — `clamp(2.25rem, 4vw, 2.9rem)`,
tabular, with a 44px brass rule under it. Ledger-style captions (uppercase,
0.06em tracking, muted) sit above each stat-tile figure.

**Layout — ordered as a narrative, not 8 peer cards.**
1. *Headline band* (framed by a 2px top rule / 1px bottom rule, borderless
   tiles): total annual payroll (dominant), active headcount, payroll
   run-rate with a QoQ delta + inline sparkline. All three are derived from
   existing endpoints — no backend change.
2. *Where the spend goes*, full width: **total payroll by country** (the
   headline figure broken down — sum of pay = headcount × salary), then
   **payroll cost trend** (line, **non-zero y-axis** so the growth slope is
   legible — a fill-to-zero area flattened an 8% move into a straight line).
3. *How individuals are paid*, 2-col grid: **pay by country (per employee)**
   and **pay by department (per employee)** — average/median of one person's
   salary — then the org-wide **salary distribution** full width.
4. *Pay equity*, its own named and rule-underlined section: gender
   representation (a headcount — always shown) and average salary by gender
   (min-group-size gated). Grouping these two under one heading is a
   values-driven layout choice — the "is our pay fair" question gets a
   named home, not scattering among detail cards.
5. *Audit*: recent salary changes feed, height-capped with a sticky header.

**"Total payroll by country" vs "Pay by country" were nearly indistinguishable
in the first cut** (both horizontal bars, by country, sorted descending,
near-homonym titles). Fixed by: renaming to *"Total payroll by country"* vs
*"Pay by country (per employee)"*; subtitles that state the contrast
explicitly ("…not per-person salary" / "…not total cost"); placing them in
different tiers (spend vs pay); and their axes reading in different units
($M vs $k). They are genuinely different questions — CLAUDE.md views #3 and
#1 — so both stay.

**Charts state their finding.** Bars are sorted by value, not
alphabetically — salary-by-country/department by **median descending**
(median, not mean: a few large salaries skew the mean, and the typical
employee is the HR-analyst's lens). Cards carry a one-line computed insight
in the subtitle where one is meaningful ("The top 3 countries account for
69% of total payroll", "+27.4% over 8 quarters").

**Suppressed pay-equity figures** render as a labelled state — a 45° hatch
swatch plus literal text ("Withheld, fewer than N in group"), never a zero
bar, never dropped silently, never colour/pattern alone.

**Accessibility.** Every chart ships a toggleable data table (with a
visually-hidden `<caption>` and `<th scope>`); focus rings are visible on
all filters and toggles; the QoQ delta pairs an arrow glyph + sign with the
colour; contrast is AA (ink ~13:1, muted ~5.2:1, series ≥ 3:1). Verified in
light and dark at desktop and 430px.

## Analytics dashboard — load performance

The first cut of the dashboard was slow to load. Two compounding causes:

- **Backend.** Each analytics endpoint is a thin pass-through, and 5 of the
  8 view functions independently call `get_current_salary_snapshots()` — a
  `ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY effective_date DESC,
  id DESC)` window query over the whole salary history.
  `payroll_trend_by_quarter` ran that query **once per quarter** (8× for the
  default view). One dashboard load = **13 executions** of that window query
  across 8 HTTP endpoints.
- **Frontend.** 9 card components each fetched independently with no dedup
  or cache — **12 requests for 8 endpoints** (`salary-by-department` ×3,
  `headcount-payroll-by-country` ×2, `payroll-trend` ×2), doubled again in
  dev by React StrictMode.

The fix, in order of impact:

1. **`get_current_salary_snapshots()` is computed once per dashboard load.**
   The 5 current-state views gained an optional trailing `snapshots=` param;
   a new `dashboard_summary()` computes the list once and threads it into
   all of them, then adds gender ratio, the recent-changes feed, and the
   payroll trend. Exposed as `GET /analytics/dashboard` returning every view
   in one response. The 8 per-view endpoints stay — the 3 filterable cards
   still call them when a filter moves off its default, and the stretch
   NL-query feature targets the service functions.

2. **`payroll_trend_by_quarter` resolves from a single fetch.** All salary
   records up to `as_of` are fetched once, grouped and sorted per employee,
   then each quarter's "current" record is a `bisect_right(...) - 1` into
   that list. Ordering by `(employee_id, effective_date, id)` reproduces the
   window's `ORDER BY effective_date DESC, id DESC` + `rn == 1` tie-break —
   pinned by a test that compares the output to per-quarter
   `get_current_salary_snapshots` resolution. One behaviour changed: the old
   inner join to `employee` silently dropped salary rows pointing at a
   missing employee; with `foreign_keys=ON` such orphans can't exist.

3. **Composite index `(employee_id, effective_date)` on `SalaryRecord`**,
   matching the window query's partition/sort. The standalone `employee_id`
   index was dropped (it's the leftmost prefix of the new one).

4. **SQLite PRAGMAs on connect** (`app/db.py`): `journal_mode=WAL` +
   `synchronous=NORMAL` so dashboard reads don't contend with the seed
   transaction / CRUD writes; `temp_store=MEMORY` for the window sort;
   `foreign_keys=ON` (SQLite leaves FK enforcement off by default — every
   write path already inserts parent-before-child). The pragma body is a
   plain function bound to the app engine via a `connect` event, so the
   in-memory test engine in `conftest.py` is untouched.

5. **Frontend fetches the dashboard once.** `AnalyticsPage` calls
   `useDashboardData()` and passes slices to the cards as props; the 5
   static cards became presentational, and the 3 filterable cards take their
   default result from props and only self-fetch off-default. 12 requests →
   1 on load (2 in dev under StrictMode).

**No response cache.** After 1–4 the endpoint is ~1 window query + a
`COUNT` + a bounded join + one trend fetch (~0.15s locally against the 10k
seed). A short-TTL cache would have added a staleness window after a write —
during a demo a reviewer who adds an employee and reloads would see stale
aggregates — for a gain that no longer mattered.

## NL analytics query: the model selects a function, it never touches data

Phase 8. `POST /analytics/ask` takes a plain-English question and returns
one of the 8 analytics views. The design constraint that drove everything
else: **the LLM has no write path and never generates SQL.** It picks a
function name + typed parameters from a fixed registry
(`app/services/nl_query.py` `FUNCTION_SPECS`); the backend then calls the
same, already-tested `app/services/analytics.py` function the REST endpoints
and the dashboard use. No query logic is duplicated, and the model's only
influence on the database is *which* of 8 read queries runs and with what
bounded arguments.

Why not let the model generate a query, or expose write actions:
compensation changes (raises, promotions, corrections, new employees) are
deliberate decisions with an audit trail — they stay in explicit,
human-confirmed UI forms. Interpreting "give the Berlin team a raise" from a
sentence is exactly the wrong place for ambiguity. So the NL feature is
read-only by construction, not by policy: there is no code path from it to a
mutation, and a write-flavoured question (`"give everyone 10%"`) resolves to
the same fixed out-of-scope reply as `"what's the weather"`.

Other decisions:

- **Function-selection, not tool-calling.** The model is asked for a plain
  JSON object `{"function": ..., "parameters": {...}}` via
  `response_format: json_object`, not OpenRouter's tool API. Simpler to
  parse and validate, and it keeps the allowlisted-model requirement (see
  below) unentangled from per-model tool-schema quirks. A reply that isn't
  that shape, or names nothing in the registry, is treated as out-of-scope.
- **Parameters are bounded server-side.** The model's `months`, `limit`,
  `quarters`, `change_type` are coerced and clamped to the *same* ranges the
  REST endpoints enforce (`app/routers/analytics.py` `Query(ge=, le=)`), with
  a human-readable note when a value is adjusted. A bad value degrades to the
  default; it never reaches a query function unchecked.
- **The OpenRouter call is one injectable seam.** `default_model_caller` is
  the only function that does I/O; `run_nl_query` takes it as a parameter and
  the endpoint supplies it through a FastAPI dependency. Every test passes a
  canned caller — the suite makes no network calls.
- **HTTP mapping.** `ok` / `out_of_scope` → 200 (out-of-scope carries the
  fixed message and null data — it's a valid answer, not an error). Model
  unreachable or unconfigured → 503 with a generic message; the upstream
  error text is not forwarded to the client.

## OpenRouter model allowlist is a hardcoded code-level guard

`app/openrouter.py` holds a `frozenset` of permitted model IDs, all
free-tier (`:free`), and `resolve_openrouter_model()` is the only place a
model ID is chosen — it returns the hardcoded default or a value it has just
checked against the set, otherwise raises. This is deliberately **not** a
Settings field: OpenRouter's free-vs-paid routing has silently run accounts
into a negative balance before, so the rule is that the set of callable
models can only change via a commit to this file, never via an env var,
config, or request payload. Import-time asserts fail the process if the
default drifts off the list or a non-`:free` ID is added.

The allowlist was checked against `https://openrouter.ai/api/v1/models` on
2026-09-04. Two findings worth recording:

- The `meta-llama/llama-3.1-8b-instruct:free` ID cited as the example in
  `CLAUDE.md` / `requirements.md` **no longer resolves** — OpenRouter
  delisted the free Meta Llama tier upstream around Aug 2026. A test
  (`test_openrouter_config.py`) guards against it being pasted back.
- The free tier shares one upstream pool across all OpenRouter users, so any
  free model 429s intermittently regardless of your own usage. During the
  smoke test two of three allowlisted models were rate-limited and
  `nvidia/nemotron-3-super-120b-a12b:free` was not — it's the current
  default. `default_model_caller` retries once on a 429 with a short backoff
  before giving up. `max_tokens` is 600, not ~300, because that model spends
  completion tokens on reasoning before it emits the JSON object.