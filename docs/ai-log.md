# Salary Management Software — AI Logs

## Phase 1 — Data models (SQLModel)

**Asked**: implement the locked `User`/`Employee`/`SalaryRecord` schema from
CLAUDE.md as SQLModel models, plus DB init wired into FastAPI startup.

**Produced**: models with enums for role/gender/status/change_type, a
bidirectional `Employee.salary_records` / `SalaryRecord.employee`
relationship across two files, and `init_db()` called from a FastAPI
lifespan handler.

**Accepted as-is**: the schema/field layout, index choices (email
uniqueness, country/department/status/effective_date indexes anticipating
Phase 4 analytics queries).

**Corrected**: the initial cross-file `Relationship()` typing used
`from __future__ import annotations` with builtin `list["SalaryRecord"]`,
which SQLAlchemy's forward-ref resolver can't parse (it expects `List[...]`
from `typing`, not a stringified generic). Caught immediately by running the
sanity-check test rather than assuming it worked; fixed by dropping the
`__future__` import and using `typing.List`.

## Phase 2 — Seed script generation logic

**Asked**: a seed script generating 10,000 correlated employees (salary
derived from country/department/level reference tables, not independently
random) plus realistic salary history for ~15-20% of them, per CLAUDE.md.

**Produced**: `app/seed/reference_data.py` (country/department/level tables
with fixed FX rates and pay multipliers), `app/seed/generate.py` (employee +
salary-history generation with a fixed random seed), `app/seed/run.py`
(clear-and-bulk-insert orchestration).

**Accepted as-is**: the reference table shape and weighting (country/dept/
level distributions, ~18% history rate, ~20% of history employees also
getting a future-dated raise to exercise the current-salary exclusion
logic), after manually querying the seeded SQLite file and confirming
aggregate numbers were internally consistent (US > lower-cost-tier
countries, Engineering > Support) rather than trusting the generation logic
by inspection alone.

**Corrected**: that same manual verification surfaced a real bug —
`change_type` values were being persisted as `"raise_"` instead of `"raise"`
for one enum member, due to a SQLAlchemy default (Enum columns persist by
member `.name`, not `.value`). Not something code review would likely have
caught; found by actually querying seeded data and checking distinct
`change_type` values against the CLAUDE.md contract. See design-notes.md for
the fix (`enum_column()` helper with `values_callable`).

## Phase 6 — raise vs. promotion, and payroll scope

**Asked** (by the user, mid-review of the salary-record form): what's the
actual difference between `change_type` "raise" and "promotion" in this
system, and does the software track monthly salary payments at all.

**Produced**: a direct answer from what was actually true at the time —
payroll disbursement tracking is explicitly out of scope per
`docs/requirements.md`; and raise/promotion were functionally identical
in the implementation (only the stored label differed, `Employee.role`
was never touched by either). Rather than silently pick a resolution,
posed the coupling question back to the user (should recording a
promotion also update the employee's title, or stay decoupled as
today) since it changes the interaction model, not just an internal
implementation detail.

**Accepted**: user chose to couple them. Implemented
`SalaryRecordCreate.new_role` (optional) — when set, `Employee.role`
updates in the same commit as the `SalaryRecord`, so a promotion's title
change can't be saved separately and forgotten. Frontend only shows the
field when change_type = promotion; backend stays generic. Documented
the raise/promotion distinction inline in `ChangeType` (previously
undocumented beyond the member name) and in design-notes.md, and added
tests for both the coupled and uncoupled cases.

## Phase 6 — three corrections to the "add salary record" / bulk raise UX, all user-caught

None of these were things I flagged myself before shipping — the user
caught each one in review, and each turned out to be an actual
correctness or data-integrity gap, not just a UI preference:

1. **"Hire" was offered as a change_type option even for an employee who
   already had salary history.** Doesn't make sense — you don't re-hire
   someone already employed. Fixed at the service layer
   (`create_salary_record()` rejects a second hire for any employee with
   existing history, any change_type), not just hidden in the dropdown —
   confirmed a direct API call is blocked too, not only the UI.
2. **Bulk raise offered a `status` filter (active/inactive/all).** User's
   point: a raise for someone who already left the company was never a
   real scenario, so "inactive"/"all" shouldn't have been offered as
   choices at all. Removed the parameter entirely rather than just
   changing the default — added a test confirming a stray `"status"` key
   in the request body is silently ignored, not accepted.
3. **Bulk raise accepted negative percentages as a "pay cut."** User's
   point: a negative percentage inserts a `SalaryRecord` with
   `change_type = "raise"` whose amount is *lower* than the prior one,
   which reads as self-contradictory in the salary history table.
   Restricted to strictly positive percentages — `docs/requirements.md`
   only ever asked for "apply a % raise," so a real bulk pay-cut feature
   (if ever needed) deserves its own `change_type` concept, not a sign
   flip on this endpoint.

Pattern worth naming: in each case the fix was to make the *system*
reject the bad state (service-layer validation, parameter removed
outright), not just adjust a UI default — consistent with how the
gender-suppression rule and the future-dated-salary exclusion were
already implemented in the query/service layer per CLAUDE.md's testing
philosophy, rather than left to the frontend to hide.