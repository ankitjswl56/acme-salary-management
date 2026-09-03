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

---

## Phase 7 — analytics dashboard visual design

**Ask:** the dashboard was functionally correct but visually generic
(default x-charts colours, a flat wall of identical full-width bar cards).
Wanted it to feel like a considered financial / people-ops tool, and asked
for a written design plan *reviewed against genericness* before any code —
"would this same plan come out of any 'make a dashboard' prompt?"

**AI-produced plan, then challenged:**

- *Palette.* First proposed teal + gold. Ran every candidate pair through
  the dataviz skill's `validate_palette.js` rather than eyeballing —
  teal failed the chroma floor at mid-lightness in ~6 attempts. Settled on
  bond-indigo `#3A4E9C` + brass `#BE8636` (both modes clear CVD ΔE ≥ 18,
  contrast ≥ 3:1). Kept the reasoning that's *specific* to comp data: gold
  tied to the median series + headline figure (currency), red reserved for
  a payroll drop only, explicitly not finance-green.
- *Genericness pass changed three things:* dropped a donut for gender ratio
  (reflex choice) → single-hue sorted bars with share labels; dropped
  "rounded cards + soft shadows" → hairline borders, no elevation; and
  reframed "important numbers on top" into a *named Pay Equity section* +
  a payroll headline with a QoQ burn delta, which is the figure a
  people-ops lead is actually accountable for.
- *Country chart sort:* user suggested value-sort over alphabetical; AI
  extended it to sort by **median** specifically (robust to a few large
  salaries) and made the data table follow the same order.

**Accepted as-is:** the four-tier layout, the non-zero y-axis on the payroll
trend line (a fill-to-zero area had flattened an 8% move), the computed
one-line insights in card subtitles, the hatch-swatch suppressed state.

**Corrected during build:** x-charts v9 moved `barLabel` onto the series
object and `categoryGapRatio`/`barGapRatio` onto the band-axis config (not
the chart) — both caught by typecheck, not docs. `titleTypographyProps` on
CardHeader is gone in v9 (leaked to the DOM as an attribute at runtime, no
type error) — switched to `slotProps`.


---

## Analytics dashboard — load performance

**Ask:** "the analytics page is way too slow ... 22-25 API calls at once on
page load. what do you suggest?"

**Diagnosis (two Explore agents, one Plan agent).** Backend: 5 of 8 view
functions each recompute the `ROW_NUMBER() OVER (PARTITION BY employee_id
...)` window query, and `payroll_trend_by_quarter` ran it once per quarter —
13 executions of the expensive query per dashboard load. Frontend: 12
requests for 8 endpoints (4 exact duplicates, one being `useDepartmentOptions`
called by two cards), no dedup/cache layer, doubled to ~24 in dev by
StrictMode.

**Options weighed with the user:** (a) how far to go — chose the core fix
(aggregate endpoint + single-query trend + composite index + WAL + frontend
rewire) over a backend-only or "core + client dedup" scope; (b) a 60s
response cache — declined, since after the query reduction the endpoint is
~0.15s and a cache only buys instant re-nav at the cost of post-write
staleness during a demo.

**Accepted as designed:** the `snapshots=` injection param on the 5 views;
`dashboard_summary()` bundling the 3 filterable views with their
endpoint-default params so the payload is byte-identical to first paint;
the `bisect_right` trend rewrite; presentational static cards + "initial
data from props, self-fetch only off-default" for the filterable ones.

**Corrected during build:** the filterable cards can't just render
`data ?? initialData` — `useAnalyticsQuery` keys off `queryKey`, so once the
dashboard payload arrives the effect doesn't re-run and `data` stays the
empty first value. Fixed by rendering `initialData` directly while filters
are at their defaults and only reading the hook's `data` once a filter
diverges.

**Verified:** 130 backend tests green (incl. a trend-equivalence test and a
"snapshots computed once" test); one dashboard request on load (two in dev
under StrictMode); each filter change fires exactly one scoped request;
dashboard renders identically.
