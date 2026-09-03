# Progress Checkpoint

Written to let a fresh session resume this project without the prior
conversation history. Read this, `CLAUDE.md`, and `docs/requirements.md`
before doing anything else — this file assumes both.

**Status as of this checkpoint**: Phases 0–6 of `CLAUDE.md`'s build plan
are complete and committed. Phase 7 (analytics dashboard frontend) is
next and has not been started.

## Phase-by-phase status

| Phase | What | Status | Key commits |
|---|---|---|---|
| 0 | Scaffold (FastAPI + Vite + Docker Compose) | ✅ done | `84e801d` |
| 1 | Data models (User/Employee/SalaryRecord) + DB init | ✅ done | `dfd8cf9` |
| 2 | Seed script (10k employees + 3 demo users) | ✅ done | `7c5a602`, `9ffbe52` |
| 3 | Core CRUD (employees, salary records) + tests | ✅ done | `a8f7494`, `4678434`, `99667b5` |
| 4 | Analytics endpoints (8 views) + tests | ✅ done | `9cf5dde`, `631a2a4`, `41cb680`, `8f116d1` |
| 5 | Auth/RBAC (JWT login, role gating) | ✅ done | `3eebfe6`, `77fed69` |
| — | JS→TS migration (not in original plan, done ahead of Phase 6 UI work per user request) | ✅ done | `9604626` |
| 6 | Frontend: employee list/detail/forms, bulk raise, CSV import | ✅ done | `6ac8566` → `4e796ec` (see below) |
| 7 | Frontend: analytics dashboard (8 views, role-gated) | ⬜ **not started — next up** | — |
| 8 | Stretch: NL query via OpenRouter | ⬜ not started (build only if 0–7 solid, per CLAUDE.md) | — |
| 9 | Polish (README/docs pass, fresh `docker compose down -v && up`, demo video) | ⬜ not started | — |

Phase 6 commits in order: `6ac8566` (auth/routing foundation) →
`8d04fc9` (employee list/detail) → `e7ae6c8` (employee create/edit forms)
→ `181cc24` (salary-record form + promotion/hire fixes) → `155f473`
(bulk raise) → `e741a89` (CSV import) → `4e796ec` (list ordering/
pagination/URL-filter UX pass).

Backend: **121 pytest tests, all passing.** Frontend: no automated test
suite exists (see Known Gaps).

## Exact next action

Build out `frontend/src/pages/AnalyticsPage.tsx` — currently a one-line
placeholder (`"Analytics dashboard — coming in Phase 7."`) — into the real
8-view dashboard. All 8 backend endpoints already exist, are tested, and
are role-gated to **any authenticated role** (admin, hr_manager,
*and* executive_viewer — this is the one part of the app executive_viewer
can actually reach; see `app/routers/analytics.py`'s router-level
`dependencies=[Depends(get_current_user)]`, no specific role required).

The 8 endpoints (all under `/analytics`, all GET), with their response
shapes (`app/schemas/analytics.py`):

1. `/salary-by-country` → `CountrySalaryStats[]` `{country, headcount, avg_salary_usd, median_salary_usd}`
2. `/salary-by-department` → `DepartmentSalaryStats[]` `{department, headcount, avg_salary_usd, median_salary_usd}`
3. `/headcount-payroll-by-country` → `CountryPayroll[]` `{country, headcount, total_payroll_usd}`
4. `/salary-distribution` → `SalaryDistributionBand[]` `{band, headcount}` (8 fixed bands, `<$30k` … `$200k+`)
5. `/gender-ratio?department=` → `GenderHeadcount[]` `{gender, headcount}` (always safe to show, it's a count)
6. `/salary-by-gender?department=&role=&min_group_size=` → `GenderSalaryStats[]` `{gender, headcount, avg_salary_usd: number|null, suppressed: bool}` — **`avg_salary_usd` is `null` and `suppressed` is `true` whenever `headcount < min_group_size` (default 5) — the frontend must render that as a real suppressed state (e.g. "insufficient data"), not treat null as a bug or coerce it to 0**
7. `/recent-changes?months=&change_type=&limit=` → `SalaryChangeFeedItem[]` `{employee_id, employee_name, department, country, change_type, effective_date, amount, currency, amount_usd}`
8. `/payroll-trend?quarters=` → `QuarterlyPayroll[]` `{quarter, headcount, total_payroll_usd}` (e.g. `"2026-Q3"`, oldest first)

None of these 8 response types are in `frontend/src/types/api.ts` yet —
add them there first, following the existing hand-mirrored pattern (see
that file's own comment: "no shared codegen between the two yet").
Likely also want a `src/api/analytics.ts` wrapper module (parallel to
`src/api/employees.ts`) and a `src/dataviz` skill load before writing any
chart code (project instructions mention a `dataviz` skill for exactly
this — check the available-skills listing for the current session).

Suggested checkpoint breakdown (matching how every other phase in this
session was paced — small, verified, user-confirmed commits, not one
giant one): types + API wrappers first, then maybe 2–3 views per
checkpoint, verifying each against the real seeded dataset in a browser
before committing. `AnalyticsPage.tsx` should probably become a container
that composes 8 smaller view components rather than one giant file.

## Non-obvious implementation details / gotchas already solved

Read this before touching related code — these were each a real bug or
design trap already hit and fixed once; don't rediscover or accidentally
revert them.

- **SQLAlchemy's `Enum` type persists by member `.name`, not `.value`, by
  default.** This silently broke `ChangeType.raise_` (member name
  `raise_`, value `"raise"`, since `raise` is a Python keyword) — records
  were saved with `change_type = "raise_"` instead of `"raise"`. Fixed via
  `enum_column()` in `app/models/enums.py` (`values_callable`), applied to
  *all four* enum columns for consistency, not just the one that broke.
  **If you add any new enum-typed column anywhere, use `enum_column()`,
  not a bare `Field()`.**
- **"Current salary" is always derived, never stored** — the latest
  `SalaryRecord` with `effective_date <= as_of` (default today). Single-
  employee: `get_current_salary_record()` in `app/services/salary.py`.
  Batch (used by all 6 "current state" analytics views, and by bulk
  raise): `get_current_salary_snapshots()` in `app/services/analytics.py`,
  a `ROW_NUMBER() OVER (PARTITION BY employee_id ...)` window query — not
  N+1 per-employee lookups. A future-dated record must never be treated
  as current until its date arrives; this is tested explicitly in
  multiple places.
- **`create_salary_record()` has two extra rules beyond "compute the USD
  snapshot"**: (1) `effective_date` can't be before `Employee.hire_date`;
  (2) `change_type = "hire"` is rejected if the employee already has *any*
  `SalaryRecord` (of any type) — a second "hire" makes no sense and is
  now blocked at the service layer, not just hidden in the UI dropdown.
- **`new_role` on `SalaryRecordCreate`** (optional): when set, updates
  `Employee.role` in the *same commit* as the `SalaryRecord` — used for
  promotions, so a title change can't be saved separately and forgotten.
  Not restricted to `change_type == promotion` at the schema/service
  level (backend stays generic); the frontend only shows the field when
  `change_type = promotion`.
- **Bulk raise** (`app/services/bulk.py`) — three deliberate restrictions,
  all added after user review caught real problems (see
  `docs/ai-log.md`'s "three corrections" entry): always active-employees-
  only (no `status` parameter exists at all, confirmed a stray `status`
  key in the request body is silently ignored); percentage must be
  **strictly positive** (no bulk pay cuts — that would insert a "raise"
  record with a *lower* amount, which is self-contradictory); applied to
  each employee's **local currency** amount, not the USD snapshot (re-
  normalizes via `normalize_to_usd()` after).
- **CSV import** (`app/services/csv_import.py`) reuses
  `create_employee()`/`create_salary_record()` per row rather than
  reimplementing validation. Two *different* failure buckets in the
  response: `errors` (row never produced an employee — bad required
  field, duplicate email) vs `salary_warnings` (employee was created
  fine, but the row's amount/currency failed validation). They're
  different because `create_employee()` and `create_salary_record()`
  each commit independently — by the time a salary error surfaces, the
  employee is already durably committed, so there's nothing to roll back
  even if both were reported as the same kind of failure. Reads the
  upload as `utf-8-sig`, not `utf-8` (Excel BOM handling).
- **`Employee.country` stores a reference-data *code*** (e.g. `"US"`),
  not a display name. `GET /employees/filters` resolves each distinct
  code to its full name via `app/reference_data.py`'s `COUNTRIES` list
  (the same table the seed script draws from) for the country dropdown —
  falls back to the code itself if not found. `department` values are
  already human-readable strings, no such mapping needed there.
- **`GET /reference/currencies`** exposes `SUPPORTED_CURRENCIES` from
  `app/services/currency.py` for the salary-record currency dropdown —
  same "source live from backend, don't hardcode a second copy" pattern
  as `/employees/filters`, justified because currency *is* validated
  against a real backend allowlist (unlike country/department, which are
  just plain strings with no enum).
- **Employee list ordering**: `Employee.id DESC` (most recently added
  first). There's no `created_at` column on `Employee` (schema is
  locked per `CLAUDE.md`) — `id` is used as a reliable proxy since it's
  sequential on insert in this app's usage pattern.
- **Employee list filters/pagination live in the URL** (`useSearchParams`
  in `EmployeesPage.tsx`), not local-only React state — survives a
  browser refresh, and `Reset` is just `setSearchParams({})`. Search text
  is debounced locally before being pushed into the URL (`replace: true`)
  so typing doesn't spam history or fire a request per keystroke.
- **Frontend API client** (`src/api/client.ts`): `apiFetch<T>()` accepts
  either a JSON-serializable body or a `FormData` (file upload) body —
  `FormData` is passed through as-is so the browser sets its own
  multipart boundary; setting `Content-Type` manually for it would break
  that. `extractErrorMessage()` handles both FastAPI's plain-string
  `detail` (404/409/etc.) and the list-of-`{msg,...}` 422 validation-
  error shape.
- **Auth flow**: token/email/role stored in `localStorage` under key
  `acme_salary_auth`. A 401 response anywhere clears that storage *and*
  dispatches a `window` `'acme:unauthorized'` event; `AuthContext`
  listens for that event to log out — decouples the plain-fetch API
  client from React state without an extra library. `ProtectedRoute`
  enforces both "must be logged in" and "must have role X" at the
  *route* level (executive_viewer is blocked from `/employees*` routes
  entirely, not just hidden from nav) — matches backend gating exactly.
- **Docker Compose**: `node_modules`/the Python venv are baked into each
  image at build time, **not** volume-mounted (only `frontend/src`,
  `frontend/index.html`, and `backend/app` are mounted for hot-reload).
  A dependency change (new npm/pip package) needs `docker compose up
  --build`, not plain `up`, or it silently keeps using the stale image.
  Documented in the README; this actually bit us once mid-session
  (`react-router-dom` missing after a plain `up`).
- **Demo password is `Password123!@#`** (the user changed this by hand
  from what was originally seeded — see Manual Edits below). Already
  correct in the README and `app/seed/users.py`; don't "fix" it back.
- **Test fixtures** (`backend/tests/conftest.py`): `session` (in-memory
  SQLite), `client` (TestClient **pre-authenticated as hr_manager** by
  default — covers almost every existing test without each one attaching
  its own token), `unauthenticated_client`, `make_token(role, email)`
  (build a JWT for any role, for RBAC-boundary tests). Reuse these.
- **Frontend browser verification pattern used all session**: no
  `chromium-cli` available in this environment. Playwright was installed
  ad-hoc into the scratchpad dir (`npm init -y && npm install
  playwright@1.62.1`, browsers via `npx playwright install chromium`,
  already done once — shouldn't need reinstalling) and driven via small
  `.mjs` driver scripts per checkpoint, screenshotted, then torn down.
  Consider suggesting `/run-skill-generator` to the user to make this a
  reusable project skill — flagged as worth doing, never actually done.
- **Seed script** (`python -m app.seed` from `backend/`, or `docker
  compose exec backend python -m app.seed`) is safe to re-run — clears
  and repopulates `Employee`/`SalaryRecord`/`User` each time, fixed
  random seed (42) so the dataset is reproducible run to run.

## Manual edits the user made directly (not generated by Claude)

Both already committed and reflected everywhere they need to be — noted
here only so they aren't mistaken for accidental drift and "corrected"
back in a future session.

1. **`backend/app/seed/users.py`**: `DEMO_PASSWORD` — the user changed it
   from `"Password123!"` (what Claude originally wrote) to
   `"Password123!@#"`, mid-Phase-2, before the first commit that included
   it. Current value is correct and already matches the README.
2. **`backend/app/models/enums.py`**: the inline comments on
   `ChangeType.correction` and `ChangeType.cola` (explaining what each
   means) were added by the user directly to the file, also mid-Phase-2,
   before Claude's next edit to that file. Comments on `raise_` and
   `promotion` were added later *by Claude* (Phase 6, commit `181cc24`)
   to match the same style once the raise/promotion distinction became a
   real discussion — see `docs/ai-log.md`'s "Phase 6 — raise vs.
   promotion" entry.

## Known gaps / deferred items

- **No frontend for the 8 analytics views yet** — this is Phase 7, the
  next action (see above). `AnalyticsPage.tsx` is currently a one-line
  placeholder.
- **No automated frontend test suite.** Backend has 121 pytest tests;
  frontend has zero committed test files. All frontend verification this
  session was done via ad-hoc Playwright driver scripts run manually and
  discarded (scratchpad only, never committed) — real, but not
  repeatable/CI-able. If "meaningful tests" grading extends to frontend,
  this is a gap worth raising with the user rather than assuming it's
  fine.
- **CSV import has no file size / row count limit.** Documented as a
  deliberate scope cut in `docs/design-notes.md` given this assessment's
  scale, not a silent oversight — would need one for real production use.
- **Stretch NL-query feature (Phase 8) not started.** Per `CLAUDE.md`,
  build only if Phases 0–7 are solid, and only with the OpenRouter
  guardrails already specified there (hardcoded free-tier model
  allowlist, reject/refuse any other model, polite fallback when the
  model's function-selection doesn't match one of the 8 analytics
  functions). `.env` at the repo root already has a real
  `OPENROUTER_API_KEY` (gitignored, never committed) ready for this.
- **Phase 9 polish not started**: no fresh `docker compose down -v &&
  up` validation pass done recently (though individual dependency-adding
  checkpoints were each verified via a full rebuild — see the git log
  for "docker compose down && up --build" mentions), no demo video, and
  `README.md`/`docs/requirements.md` haven't had a final consistency
  pass against the finished Phase 0–6 feature set.
- **Bulk raise / CSV import have no undo mechanism** — by design,
  consistent with the append-only philosophy (each write is just another
  `SalaryRecord`/`Employee` row within the existing model), but worth
  being aware of if asked about it — there's no "undo this batch" button.