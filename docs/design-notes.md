# Salary Management Software — Design Notes

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