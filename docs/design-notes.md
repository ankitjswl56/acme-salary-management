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