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