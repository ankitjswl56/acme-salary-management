# Progress Checkpoint

Written to let a fresh session resume this project without the prior
conversation history. Read this, `CLAUDE.md`, and `docs/requirements.md`
before doing anything else — this file assumes both. `docs/design-notes.md`
and `docs/ai-log.md` carry the "why" behind the decisions summarized here.

**Status as of this checkpoint**: Phases 0–8 of `CLAUDE.md`'s build plan are
complete and committed, including the stretch NL-analytics-query feature.
Phase 9 (polish) is nearly done — fresh-rebuild validation, RBAC walk-through,
graceful-degradation check, README pass, and a first frontend test suite are
all done. **Only the demo video and a final human review of the whole thing
remain.**

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
| 6 | Frontend: employee list/detail/forms, bulk raise, CSV import | ✅ done | `6ac8566` → `4e796ec` |
| — | Auto-seed DB on first startup (zero-step reviewer setup) | ✅ done | `55924ef` |
| 7 | Frontend: analytics dashboard (8 views, role-gated) | ✅ done | `be68bbb` → `5416fd9` (see below) |
| 8 | Stretch: NL query via OpenRouter | ✅ done | `630c7fc` → `81b2e3d` (see below) |
| 9 | Polish (README/docs pass, fresh rebuild, frontend tests, demo video) | 🟡 **mostly done** — demo video + final review left | `8d9381b`, `17b4285` |

Phase 7 commits in order: `be68bbb` (add MUI) → `421fdb0` (add
`@mui/x-charts`) → `db3ecc1` (analytics API types + client wrappers) →
`af94e63` (dashboard — 8 views, tiered comp-tool design) → then a
load-performance pass: `2b0011e` (SQLite WAL/FK/temp-store pragmas) →
`e3f716e` (`(employee_id, effective_date)` composite index) → `129f102`
(snapshot views accept a precomputed list) → `84ede32` (payroll trend from
one fetch, not one window query per quarter) → `71a479a` (`dashboard_summary`
service) → `f0ddf56` (`GET /analytics/dashboard`) → `2e8709d` (`getDashboard`
wrapper + `AnalyticsDashboard` type) → `af2bbd1` (page fetches once, cards
render from props) → `5416fd9` (docs: perf decisions).

Phase 8 commits in order: `630c7fc` (OpenRouter model allowlist guard) →
`15d08b6` (`nl_query.py` — question → one of the 8 analytics functions) →
`7b6c3c1` (`POST /analytics/ask` endpoint) → `a987600` (chore: ignore
`*.db-wal`/`*.db-shm`) → `81b2e3d` (frontend "Ask a question" box on the
dashboard). Docs for Phase 8 land in the same commit as this checkpoint.

Backend: **192 pytest tests, all passing** (`cd backend && .venv/bin/python
-m pytest -q` — the venv is at `backend/.venv`). Frontend: `tsc -b` clean,
`oxlint` clean, and **29 Vitest tests** (`cd frontend && npm test`) covering
the NL-query box, the admin Users page, `ConfirmDialog`, and the bulk-raise
confirm flow; the rest of the UI is `tsc`-only
(see Known Gaps).

## Exact next action

Phase 9 — polish. Almost everything is done; what's left needs a human:

1. **Record the demo video.** Suggested flow: `docker compose up --build`
   from clean → land as each of the 3 roles (admin/hr → `/employees`, exec →
   `/analytics`, exec blocked from `/employees`) → dashboard walk-through →
   the "Ask a question" box (a real question + a write-flavoured one that
   refuses) → as admin, the Users page (create an account, change a role;
   note hr_manager has no Users link).
2. **Final read-through** of `README.md` and `docs/requirements.md` with
   fresh eyes for anything stale against the shipped Phase 0–8 feature set.
   (Per CLAUDE.md, `requirements.md` is reference-only — don't rewrite it;
   the one known wording gap, "answer in natural language", is deliberately
   documented in `docs/design-notes.md` instead.)

Already done this phase:

- **ConfirmDialog replaces `window.confirm()`** (`0494dae`) — bulk raise and
  Users "Remove" now open a real styled modal (`src/components/
  ConfirmDialog.tsx`: title, wrapping body, Cancel/Confirm, a `danger`
  variant, a `confirming` busy state, Esc/backdrop-click to cancel) instead
  of the browser's own dialog. Both call sites needed a control-flow change
  — `window.confirm()` blocked synchronously in the submit handler; the
  modal instead opens on submit and the real API call moves into
  `onConfirm`. Details in `docs/design-notes.md`.
- **Admin user-management** (`bfc917d`, `4d1c304`) — the one RBAC capability
  admin has over hr_manager, previously speced but unbuilt. `GET/POST/PATCH/
  DELETE /users` behind `require_role(admin)`; an admin-only `/users` page
  (route- and nav-guarded). Self-lockout guards (can't demote/delete
  yourself). No "deactivate" — the locked `User` schema has no `is_active`,
  so delete is how access is revoked. Details in `docs/design-notes.md`
  ("Admin vs hr_manager").
- **UI polish** (`4cef7e7`, `e338b18`) — status pills (green active / grey
  inactive) in the employee list + detail; the Reset button takes the
  accent colour once there's a filter to clear; the analytics "Ask a
  question" box got a brass left-rule + tint + sparkle glyph so the stretch
  feature reads as distinct without breaking the dashboard's hairline
  aesthetic. Deliberately *not* touched: adding free-text countries/
  departments (needs a schema change + pressures the currency/seed model —
  see the AskUserQuestion decision; deferred).
- `docker compose down -v && up --build` from clean — twice, incl. after the
  frontend test deps landed. First-boot auto-seed → 10,000 employees;
  dashboard total $637.5M; all 3 roles' login + routing + RBAC redirects
  confirmed in a browser; NL query works end-to-end through Docker (a
  transient OpenRouter 429 → 503 was seen once — the documented free-pool
  behaviour, recovered on retry).
- Graceful-degradation check: backend restarted with a blank
  `OPENROUTER_API_KEY` → `POST /analytics/ask` returns 503, everything else
  200.
- README: test section now lists both suites; the Phase 8 section + the
  local-dev `backend/.env` caveat were already added in `37e1316`.
- Frontend test suite added (see the test-count line above and Known Gaps).

Do **not** retrofit Phases 1–6 to MUI or add features — Phase 9 is
validation and docs only.

## Phase 8 — how the NL query is wired (read before touching it)

**Path:** `frontend` "Ask a question" box (`NLQueryBox.tsx`) →
`askAnalytics()` → `POST /analytics/ask` → `router.ask` → `nl_query.run_nl_query`.

- **`backend/app/openrouter.py`** — the hardcoded model allowlist
  (`frozenset`, free-tier only) + `resolve_openrouter_model()`. **Not** a
  Settings field on purpose: no env var / config / request can widen the set
  of callable models. Import-time asserts enforce "default is on the list"
  and "every entry is `:free`". Current default:
  `nvidia/nemotron-3-super-120b-a12b:free` (the other two allowlisted models
  were upstream-429ing during the build — free tier is a shared pool). The
  `meta-llama/...:free` id from `CLAUDE.md` is **dead** (delisted Aug 2026)
  and a test guards against re-adding it.
- **`backend/app/services/nl_query.py`** — `FUNCTION_SPECS` is the fixed
  registry of the 8 analytics functions with typed param specs; each
  `runner` calls the real `app/services/analytics.py` function (no query
  logic duplicated). `run_nl_query(session, question, *, model_caller=None)`:
  asks the model for `{"function", "parameters"}` JSON, parses it (strips
  ``` fences), and if it names nothing in the registry / isn't that shape →
  fixed `OUT_OF_SCOPE_MESSAGE`. Params are coerced + clamped to the REST
  endpoints' bounds with human-readable `notes`. **There is no code path
  from here to a write** — a "give everyone a raise" question resolves to
  out_of_scope like any other non-analytics question.
- **The OpenRouter HTTP call is `default_model_caller`** — the only I/O
  function. `run_nl_query` takes it as a param; the endpoint injects it via
  the `get_model_caller` FastAPI dependency. **Every test overrides it with
  a canned function — the suite makes no network calls.** It retries once on
  a 429 (shared-pool rate limiting), `max_tokens=600` (the default model
  emits reasoning tokens before the JSON).
- **`POST /analytics/ask`** is on the existing `/analytics` router, so it
  inherits `dependencies=[Depends(get_current_user)]` — any authenticated
  role, same as the rest of analytics. `NLQueryRequest` rejects blank /
  >500-char questions → 422. `run_nl_query` result maps: `ok` /
  `out_of_scope` → 200; `error` (model unreachable / `OPENROUTER_API_KEY`
  unset) → 503 with a generic message (upstream error text not forwarded).
- **Frontend** (`NLQueryBox.tsx`, rendered near the top of `AnalyticsPage`):
  input + Ask + example chips. `ok` → function chip + param chips + notes +
  a generic table (columns inferred from rows, USD applied to
  salary/payroll columns); `out_of_scope` → info alert; `ApiError` → error
  alert (friendlier text for 503). No history, no follow-ups — it's a demo
  of the integration, not a chat UI.
- **Local dev caveat:** `settings.openrouter_api_key` resolves from
  `backend/.env` when running uvicorn from `backend/` (pydantic-settings
  `env_file=".env"`), **not** the repo-root `.env`. Docker Compose passes it
  through from the root `.env`. With no key the feature is disabled (503),
  nothing else affected.

## Phase 7 — how the dashboard is wired (read before touching analytics code)

**One request per page load.** `AnalyticsPage.tsx` calls
`useDashboardData()` → `getDashboard()` → `GET /analytics/dashboard`, which
returns an `AnalyticsDashboard` object with all 8 views' data plus `as_of`
(see `frontend/src/types/api.ts`, mirrors `backend/app/schemas/analytics.py`).
The page passes slices of that payload to each card as props. The 5 static
cards (headline band, headcount/payroll by country, payroll trend, the two
per-employee salary-comparison cards, distribution) are purely
presentational — they never fetch.

**The 3 filterable cards** (`GenderRepresentationCard`, `SalaryByGenderCard`,
`RecentChangesCard`) take their default-parameter result from props
(`initialData`) and only issue their own request — via the per-view wrappers
in `frontend/src/api/analytics.ts` — when a filter moves off its default.
Gotcha already solved: they can't render `data ?? initialData`, because
`useAnalyticsQuery` keys its effect off `queryKey` only, so `data` stays
`null` until a filter actually changes. They render `initialData` directly
while filters are at defaults and switch to the hook's `data` once a filter
diverges. Don't "simplify" this back.

**The 8 per-view endpoints still exist** (`/analytics/salary-by-country`
etc.) and are still tested — they serve the filter-driven refetches above,
and Phase 8's NL-query feature calls the same underlying service functions.
`dashboard_summary()` in `backend/app/services/analytics.py` computes
`get_current_salary_snapshots()` **once** and threads it into the 5 current-
state views (they each take an optional trailing `snapshots=` param), then
adds gender ratio, the recent-changes feed, and the payroll trend. Full
rationale + the 13-window-query diagnosis in `docs/design-notes.md`
("Analytics dashboard — load performance").

**Charting**: `@mui/x-charts` v9 (`BarChart`, `LineChart`, `PieChart`),
sharing the MUI theme. Every chart card ships a toggleable data table
alongside it (visually-hidden `<caption>`, `<th scope>`) so figures are
never chart-only. `ChartCard.tsx` is the shared shell (title, subtitle,
optional computed insight line, chart/table toggle). Palette: bond-indigo
`#3A4E9C` (primary/single series) + brass-gold `#BE8636` (median comparison
series + headline underline); alarm-red `#B23B3B` reserved only for a QoQ
payroll drop. Dark mode lightens the indigo to `#7C8EDC`. All hexes were run
through the dataviz skill's palette validator. Full visual spec in
`docs/design-notes.md` ("Analytics dashboard — visual design").

**x-charts v9 API gotchas** (all hit during the build): `barLabel` is on the
series object, not the chart; `categoryGapRatio`/`barGapRatio` are on the
band-axis config, not the chart; `titleTypographyProps` on `CardHeader` is
gone — use `slotProps`. First two are caught by typecheck; the third leaks
to the DOM at runtime with no type error.

**Role-gating** — three roles, all three can see the dashboard:

- Backend: the `/analytics` router uses `dependencies=[Depends(get_current_user)]`
  (any authenticated user), **not** `require_role([...])`. This is the one
  surface `executive_viewer` is scoped to.
- Frontend routing (`App.tsx`): `/analytics` sits under the plain
  `<ProtectedRoute />` (logged-in only). The `/employees*` routes are the
  ones wrapped in `<ProtectedRoute allowedRoles={['admin', 'hr_manager']} />`
  — `executive_viewer` hitting them is redirected to `/`.
- `HomePage` redirects admin/hr_manager → `/employees`, everyone else
  (i.e. `executive_viewer`) → `/analytics`.
- `Layout.tsx` nav hides the "Employees" link for `executive_viewer`; only
  "Analytics" shows.

**Type gotcha for gender views**: the API sends gender as
`GenderLabel = Gender | 'unspecified'` — rows with no gender recorded are
grouped by the backend under the literal `"unspecified"`, not `null`. And
`GenderSalaryStats.avg_salary_usd` is `number | null`: it is `null` with
`suppressed: true` whenever `headcount < min_group_size` (default 5). The
frontend renders that as a labelled suppressed state (45° hatch swatch +
"Withheld, fewer than N in group" — see `SuppressedNote.tsx`), never a zero
bar, never dropped. Do not coerce the null to 0.

## Non-obvious implementation details / gotchas from earlier phases

Still current — read before touching related code. Each was a real bug or
design trap already hit and fixed once; don't rediscover or revert them.

- **SQLAlchemy's `Enum` type persists by member `.name`, not `.value`, by
  default.** Broke `ChangeType.raise_` (name `raise_`, value `"raise"`).
  Fixed via `enum_column()` in `app/models/enums.py` (`values_callable`),
  applied to all four enum columns. **Any new enum-typed column must use
  `enum_column()`, not a bare `Field()`.**
- **"Current salary" is always derived, never stored** — latest
  `SalaryRecord` with `effective_date <= as_of` (default today). Single:
  `get_current_salary_record()` in `app/services/salary.py`. Batch (all 6
  "current state" analytics views + bulk raise): `get_current_salary_snapshots()`
  in `app/services/analytics.py`, a `ROW_NUMBER() OVER (PARTITION BY
  employee_id ORDER BY effective_date DESC, id DESC)` window query — not
  N+1. Future-dated records must never count as current; tested explicitly.
- **`payroll_trend_by_quarter` no longer runs the window query per quarter**
  (perf pass) — it fetches all salary records up to `as_of` once, then each
  quarter's "current" record is a `bisect_right(...) - 1` into the per-
  employee sorted list. A trend-equivalence test pins the output against
  per-quarter `get_current_salary_snapshots` resolution. One behaviour
  change: orphan salary rows (employee missing) used to be silently dropped
  by an inner join; with `foreign_keys=ON` they can't exist.
- **SQLite PRAGMAs on connect** (`app/db.py`): `journal_mode=WAL`,
  `synchronous=NORMAL`, `temp_store=MEMORY`, `foreign_keys=ON`. Bound to the
  app engine via a `connect` event; the in-memory test engine in
  `conftest.py` is untouched. **An existing `backend/data` volume must be
  recreated (`docker compose down -v`) to pick up the `(employee_id,
  effective_date)` composite index added in the same pass.**
- **`create_salary_record()` extra rules**: (1) `effective_date` can't
  precede `Employee.hire_date`; (2) `change_type = "hire"` is rejected if
  the employee already has *any* `SalaryRecord`. Enforced at the service
  layer, not just the UI.
- **`new_role` on `SalaryRecordCreate`** (optional): when set, updates
  `Employee.role` in the *same commit* as the record — for promotions.
  Backend stays generic (not restricted to `change_type == promotion`); the
  frontend only shows the field for promotions.
- **Bulk raise** (`app/services/bulk.py`): active-employees-only (no
  `status` param exists at all); percentage must be **strictly positive**
  (no bulk pay cuts); applied to each employee's **local currency** amount,
  re-normalized via `normalize_to_usd()`.
- **CSV import** (`app/services/csv_import.py`) reuses `create_employee()` /
  `create_salary_record()` per row. Two failure buckets: `errors` (no
  employee produced) vs `salary_warnings` (employee created, salary columns
  failed) — they commit independently, so a salary failure can't roll back
  the already-committed employee. Reads upload as `utf-8-sig` (Excel BOM).
- **`Employee.country` stores a reference-data *code*** (e.g. `"US"`).
  `GET /employees/filters` resolves codes to names via
  `app/reference_data.py`'s `COUNTRIES`. `department` values are already
  human-readable.
- **`GET /reference/currencies`** exposes `SUPPORTED_CURRENCIES` from
  `app/services/currency.py` for the currency dropdown (currency *is*
  validated against a backend allowlist, unlike country/department).
- **Employee list ordering**: `Employee.id DESC` (no `created_at` column;
  schema locked; `id` is a sequential-on-insert proxy).
- **Employee list filters/pagination live in the URL** (`useSearchParams`
  in `EmployeesPage.tsx`). Search text is debounced locally before being
  pushed to the URL (`replace: true`).
- **Frontend API client** (`src/api/client.ts`): `apiFetch<T>()` accepts a
  JSON body or `FormData` (passed through as-is so the browser sets the
  multipart boundary). `extractErrorMessage()` handles both FastAPI's
  string `detail` and the 422 list-of-`{msg}` shape. A 401 anywhere clears
  `localStorage` key `acme_salary_auth` and dispatches a `window`
  `'acme:unauthorized'` event that `AuthContext` listens for.
- **`ProtectedRoute`** enforces both "logged in" and "has role X" at the
  route level — matches backend gating.
- **Docker Compose**: `node_modules` / Python venv are baked into images at
  build time, **not** volume-mounted (only `frontend/src`,
  `frontend/index.html`, `backend/app` are mounted for hot-reload). A
  dependency change needs `docker compose up --build`. This bit us once
  (`react-router-dom` missing after a plain `up`); MUI + x-charts were each
  added with a full rebuild.
- **Demo password is `Password123!@#`** (user-changed by hand — see Manual
  Edits). Correct in the README and `app/seed/users.py` already.
- **Test fixtures** (`backend/tests/conftest.py`): `session` (in-memory
  SQLite), `client` (TestClient pre-authenticated as hr_manager),
  `unauthenticated_client`, `make_token(role, email)`. Reuse these.
- **Frontend browser verification**: no `chromium-cli` in this environment.
  Playwright was installed ad-hoc into the scratchpad
  (`playwright@1.62.1`, chromium browser) and driven via small `.mjs`
  scripts per checkpoint, screenshotted, then torn down. Never committed.
  Worth making a reusable project skill (`/run` or a skill generator) —
  flagged repeatedly, never done.
- **Seed script** (`python -m app.seed` from `backend/`, or `docker compose
  exec backend python -m app.seed`) clears and repopulates
  `Employee`/`SalaryRecord`/`User` each run, fixed random seed (42). Also
  runs automatically on first startup against an empty DB (`seed_if_empty`
  in the app lifespan) so a bare `docker compose up` gives the reviewer a
  populated dashboard with no extra step.

## Manual edits the user made directly (not generated by Claude)

Both committed and reflected everywhere — noted only so they aren't mistaken
for drift and "corrected" back.

1. **`backend/app/seed/users.py`**: `DEMO_PASSWORD` changed from
   `"Password123!"` to `"Password123!@#"` mid-Phase-2. Matches the README.
2. **`backend/app/models/enums.py`**: the inline comments on
   `ChangeType.correction` and `ChangeType.cola` were added by the user
   directly. Comments on `raise_` and `promotion` were added later by Claude
   (Phase 6, `181cc24`) to match.

## Known gaps / deferred items

- **NL query depends on OpenRouter's free pool.** The default model can 429
  intermittently (shared upstream pool, unrelated to our usage); one retry
  is built in, then it's a 503 + "unavailable" box. If it's flaky during a
  demo, swap `OPENROUTER_DEFAULT_MODEL` in `backend/app/openrouter.py` to
  another allowlisted id (all are re-checked against the live model list —
  the list rotates, so re-verify before relying on it). Real network
  behaviour is only covered by a manual smoke test, never the suite.
- **NL query has no rate limiting / cost ceiling of its own.** Fine for a
  free-tier demo; a real deployment would want a per-user throttle.
- **Frontend test coverage is partial.** Backend has 192 pytest tests.
  Frontend has a Vitest suite (`cd frontend && npm test`) — 29 tests:
  `NLQueryBox` (submit / ok / out-of-scope / 503 / 422 / example-chip) +
  `nlQueryFormat.ts` formatting; `UsersPage` (self-row restrictions, create
  flow, rejected role change, delete confirm via the dialog);
  `ConfirmDialog` itself (open/closed, Esc, backdrop click, focus, confirming
  state, custom labels); `BulkRaisePage`'s confirm flow (dialog names the
  scope, cancel doesn't call the API, confirm does and renders the result).
  Everything else in Phases 1–7 is still `tsc`-only, verified historically
  via ad-hoc Playwright scripts.
  Config note: Vitest config lives in a standalone `vitest.config.ts` (not
  `vite.config.ts`) so `tsc -b` doesn't typecheck it — avoids a
  vite-version type clash with the copy Vitest bundles. `vitest@3`, not 5:
  `npm install vitest@5` reproducibly hits an npm arborist `edgesOut` bug
  on this tree.
- **No response cache on `/analytics/dashboard`.** Deliberate — after the
  perf pass the endpoint is ~0.15s locally against the 10k seed, and a
  short-TTL cache would add a post-write staleness window during a demo.
  See `docs/design-notes.md`.
- **CSV import has no file size / row count limit.** Documented scope cut in
  `docs/design-notes.md`.
- **Bulk raise / CSV import have no undo mechanism** — by design (append-
  only model), but worth knowing if asked.
- **Phase 9 polish not started**: no recent fresh `docker compose down -v &&
  up` full validation pass, no demo video, and `docs/requirements.md` hasn't
  had a final consistency pass against the finished Phase 0–8 feature set
  (README has, through Phase 8).