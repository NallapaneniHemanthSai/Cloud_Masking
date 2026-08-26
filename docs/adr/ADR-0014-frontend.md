# ADR-0014 — Frontend (React + TypeScript + Vite)

- **Status:** ACCEPTED (2026-08-26)
- **Milestone:** M14 (Frontend)
- **Related:** ADR-0013 (Backend API), ADR-0008/0009 (evaluation/failure classes), ADR-0011 (comparison),
  ADR-0002 (compute), Objective O4; milestone plan §M14.

## Objective

Deliver the **frontend** the milestone plan defines for M14: a React/TypeScript/Vite single-page app that
lets a user drive the M13 API's **core flows** — dashboard/overview, system/version/health, models +
capabilities, prediction, upload, evaluation (with per-class + thin-cloud/cloud-shadow visibility), training
& run history, telemetry/metrics, a map viewer, and the honest M11 comparison outcome. Acceptance: *the UI
talks to the API for core flows*.

## Technology & rationale

**React 18 + TypeScript 5 + Vite 6 + react-router-dom 6 + axios**, plus **leaflet/react-leaflet** for the
map viewer — exactly the stack already **declared** in `frontend/package.json` (no new runtime dependency is
introduced). This is chosen for **simplicity, maintainability, low dependency overhead, and compatibility
with the existing M13 API**, not sophistication: no Redux/MobX (React hooks + a tiny context suffice), no UI
component library (hand-written CSS keeps the bundle small and the styling auditable), no SSR. TypeScript
gives typed API contracts that mirror the M13 Pydantic schemas.

## Application structure

Under `frontend/src/` (matches the M2 scaffold folders):

- `services/` — **centralized** typed API layer: `apiClient.ts` (single axios instance), `types.ts`
  (interfaces mirroring the M13 DTOs), `api.ts` (one typed function per endpoint).
- `hooks/` — `useApiResource` (GET → loading/error/empty/data) and `useAsyncAction` (POST actions).
- `components/` — `Layout`/`NavBar`, `StatusBanner`/`RegimeBadge`, `Loading`/`ErrorState`/`EmptyState`,
  `MetricTile`, `ClassLegend`, `PerClassTable`, `ClassDistributionBar`, `JsonBlock`.
- `pages/` — `Dashboard`, `SystemHealth`, `Models`, `Predict`, `Upload`, `Evaluate`, `Comparison`,
  `History`, `Metrics`, `MapViewer`.
- `utils/` — `colors.ts` (the **M5 CloudSEN12 palette**), `format.ts`.

## API integration strategy

- **Single axios client** with base URL from `import.meta.env.VITE_API_BASE_URL` (default `/api`).
- **Dev CORS is solved by a Vite proxy** (`server.proxy` maps `/api` → the backend), so the browser makes
  **same-origin** requests and **the backend is not modified** (no CORS middleware added; M13 stays intact).
  Production is assumed to sit behind a reverse proxy that serves the SPA and forwards `/api`.
- Every UI API call maps 1:1 to a real M13 endpoint & schema; the frontend **never duplicates** backend
  training/evaluation/model logic.

## State management

Local component state + React Query-free custom hooks. A small `SystemContext` caches `/version` +
`/health` for the header. No global store library (keeps overhead low, avoids stale-state complexity).

## Loading / error / empty states

Every data view uses the shared `Loading`, `ErrorState` (shows the HTTP status + backend `detail`), and
`EmptyState` components. Actions (`/train`, `/predict`, `/evaluate`, `/upload`) show a pending state and
surface backend errors verbatim (e.g. a 503 when torch is unavailable) — never a silent failure.

## Model selection flow

`Models` page lists architectures from `GET /models` (name, version, description, aliases, `improves_over`,
supported channels/classes) and any DB-registered versions. The selected architecture + its config
parameters feed the Predict and (synthetic) Train forms.

## Prediction flow

`Predict` posts to `POST /predict` (a synthetic input by default, or an inline `(C,H,W)` image). The
response returns `output_shape` + **class pixel counts** (not mask pixels), so the UI renders the **class
distribution** with the M5 palette and a `SYNTHETIC` badge. **Full pixel-mask rendering is DEFERRED** and
clearly labelled — the current API does not return mask pixels, and the UI does **not** fabricate one.

## Evaluation visualization

`Evaluate` posts to `POST /evaluate` and renders a **per-class IoU table** (clear / thick / **thin** /
**shadow**) using the exact M5 class names and colours, with **undefined values shown as `undefined`**
(never 0), macro IoU, pixel accuracy, and thin-cloud IoU surfaced explicitly. Results carry a `SYNTHETIC`
badge (M13 `/evaluate` is synthetic validation only).

## Training / history presentation

`Predict`/`Train` runs and their records appear in `History` (`GET /history`): training runs, predictions,
evaluations, uploads — each row shows its **data-regime badge**, hashes, seed, device, and timestamp for
traceability. Train is a **bounded synthetic** action, labelled as such.

## Metrics presentation

`Metrics` page renders `GET /metrics`: uptime, total requests/errors, and a per-route latency table.

## Upload workflow

`Upload` posts a file (multipart) to `POST /upload`; the UI shows `upload_id`, `content_hash`, size, and
stored path. (Wiring an uploaded raster into `/predict` is **out of scope** — the M13 API does not read an
uploaded raster for inference; noted as future work.)

## Version / system-health display

Header + `SystemHealth`/`Dashboard` show `GET /version` (all component versions) and `GET /health` (torch
availability, resolved device, database URL).

## Reproducibility & experiment traceability

The UI surfaces the hashes/versions the API already returns (config hashes, run ids, seeds, device,
data-regime) so any displayed result is traceable to a backend record. The **Comparison** page presents the
**real M11 bounded result as REAL DATA (32-sample, 3 seeds, NOT AC-4)**, preserving the **MIXED** conclusion
(thin-cloud improved, cloud-shadow regressed) verbatim from `docs/comparison/real_experiment_cloudsen12.md`
— it invents no metrics and declares no winner.

## Accessibility / basic UX

Semantic HTML, keyboard-focusable controls, sufficient colour contrast, text labels alongside colour
(colour is never the only signal — the class legend pairs each colour with its name), responsive layout,
and a light/dark theme via `prefers-color-scheme`.

## Security boundaries

No secrets in the frontend; configuration is **environment-driven** (`VITE_*`). No auth tokens are stored
(the M13 API has no auth). The client talks only to the configured API base URL. `.env.local` is git-ignored.

## CORS assumptions

Dev: same-origin via the Vite proxy (no backend CORS needed). Prod: reverse proxy serves the SPA and
forwards `/api`. If a future deployment calls the API cross-origin directly, CORS would be added to the
backend then — **not** in M14.

## Out of scope (explicitly)

Authentication/authorization, real pixel-mask rendering (API returns counts only), geo-referenced prediction
overlay on the map (no geo-prediction endpoint), triggering real/AC-4 training from the UI, WebSockets/live
streaming, offline/PWA, i18n, a component library, and end-to-end browser test automation (M16). The map
viewer is a base map + clearly-labelled DEMO marker; prediction geo-overlay is **DEFERRED**.

## Acceptance criteria

1. `npm install` + `npm run build` succeed; `tsc --noEmit` type-checks clean.
2. The SPA starts (`npm run dev`) and, with the backend running, the Vite proxy reaches every consumed
   endpoint (`/version /health /metrics /models /predict /evaluate /history /upload`).
3. Each page has working loading/error/empty states; errors surface the backend `detail`.
4. Evaluation shows per-class metrics with thin-cloud/cloud-shadow visible and `undefined` preserved.
5. Every synthetic API result is visibly badged `SYNTHETIC`; the M11 comparison shows `REAL (bounded)` +
   `MIXED`; no fabricated real-data performance appears anywhere.
6. No backend domain logic is duplicated; M11/M12/M13 tests remain green.
