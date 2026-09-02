# Salary Management Software — Design Notes

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