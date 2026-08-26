# ADR-0015 — Integration: Degraded Mode, Recovery & NT-5 Lineage/Idempotency

- **Status:** ACCEPTED (2026-08-26)
- **Milestone:** M15 (Integration)
- **Related:** ADR-0013 (API), ADR-0014 (frontend), ADR-0008/0009 (evaluation/failure), FR-7, NFR-2,
  NFR-6, **NT-5**; Objective O4; milestone plan §M15.

## Problem

M13 (API) + M14 (UI) give a working end-to-end system, but the **operability guarantees** required by the
plan are missing: there is no **degraded-mode** response when a guardrail/validation fails, no **recovery
evidence**, and — for **NT-5** — no **lineage** or **idempotency** on the persistence layer. Today a bad
record could be silently committed, a replay could duplicate/diverge state, and provenance is incomplete.
M15 must: wire the end-to-end flow, add a documented **degraded mode + recovery**, and satisfy **NT-5**
(*detect an invalid record/state before silent commit; replay is idempotent; lineage remains complete*).

## Chosen approach (smallest that satisfies M15)

A thin **integration layer** in the existing `services` + `db` packages — **no new engine, no new runtime
dependency, no Docker/Postgres**:

1. **Lineage (NT-5):** a `LineageRow` table + `lineage_service` records, for every domain artifact, its
   type, deterministic `content_hash`, optional `parent_id`, and the input versions/hashes that produced it
   — so provenance is a complete, queryable chain.
2. **Idempotent commit + detect-before-commit (NT-5):** `commit_idempotent(...)` computes a deterministic
   key via `app.utils.hashing.stable_hash`, **validates the record first** (invalid ⇒ `GuardrailViolation`,
   **nothing is persisted**), then **get-or-create**: a replay of the same operation returns the existing
   row (no duplicate, same result). Backed by SQLite UNIQUE constraints (the substrate M13 already added).
3. **Degraded mode + recovery (FR-7/NFR-6):** a `SystemEventRow` table + `integration_service` degraded-mode
   manager. A **guardrail check** (`aggregate hides a failing subgroup` — high pixel accuracy but weak
   thin-cloud/worst-class IoU) wires the long-declared `GuardrailViolation` to **degraded mode**: it records
   a `DEGRADED` event with evidence, **labels the affected result** and prevents silent use. **Recovery** is
   an explicit operator action that records a `RECOVERY` event referencing the degraded one and marks it
   resolved — a retained recovery log.
4. **End-to-end wiring:** `run_masking_pipeline(...)` ties predict → evaluate → guardrail → lineage →
   (idempotent) persist, demonstrating the full flow and returning an operational/degraded status.

## Architecture / interfaces

New DB tables `lineage`, `system_events`; services `lineage_service`, `integration_service` (incl.
`guardrails`); API router `status` wired into `create_app`:

- `GET /status` — operational vs degraded, active degraded events, lineage count. (read-only)
- `POST /recover/{event_id}` — resolve a degraded event; append a recovery-log entry.
- `GET /lineage` — the recorded lineage chain (bounded).
- `POST /pipeline` — run the end-to-end demonstration pipeline (SYNTHETIC).

**Existing endpoints/contracts are unchanged.** The M14 frontend gains a small **additive** Status page +
header degraded indicator (reads `/status`) — no existing page is rewritten.

## Reproducibility

Idempotency and lineage keys are deterministic `stable_hash` digests (order-independent); replaying an
operation yields the identical row and hash. Lineage carries the component versions + config/content hashes.

## Security boundaries

No new secrets; configuration stays environment-driven (existing `Settings`). Recovery is an explicit,
audited action (persisted event). No auth is added (deferred). The DB stays under git-ignored `outputs/`.

## Deployment / runtime assumptions

Dev **SQLite** only; the app already initialises the schema idempotently on startup. **No change to the
Docker/compose/CI files** (those are M17). Health/version endpoints remain usable; `/status` complements
them.

## Dependency & configuration strategy

**Zero new dependencies.** Everything reuses M6–M13 + `stable_hash` + SQLAlchemy 2.0. Config via existing
`VITE_*` / backend `Settings`.

## Logging / observability

Degraded/recovery transitions are logged (structured) **and** persisted as `system_events` (the recovery
evidence FR-7 requires); `/status` and `/metrics` expose current state.

## Failure handling & rollback/recovery

Invalid records are rejected **before** commit (transactional session ⇒ no partial rows). A guardrail
failure enters degraded mode and labels the result rather than using it silently. Recovery resolves the
event and logs evidence; idempotent replay regenerates without duplication. Reverting M15 is deleting the
two tables + router (additive), and cannot break M1–M14 (existing contracts untouched).

## Alternatives considered

- A full workflow/orchestration engine or event bus — over-engineered for a single-process dev system;
  rejected.
- Redis/Postgres idempotency store or advisory locks — unnecessary at SQLite dev scale; **deferred**.
- Baking NT-1..4 fixtures here — those belong to the **M16** acceptance harness; only **NT-5** is M15.

## Deliberately deferred

NT-1..NT-4 fixtures + the full acceptance harness (**M16**); Docker/compose deployment + clean-env rebuild
(**M17**); Postgres, distributed locking, async workers, auth. Change-detection (later milestone).

## Acceptance criteria

1. **End-to-end flow works** — a pipeline smoke (predict → evaluate → lineage → persist) runs and is
   demonstrated live.
2. **Degraded mode + recovery demonstrated** — a guardrail failure enters degraded mode (labelled result,
   persisted evidence); `POST /recover` resolves it with a recovery-log entry; `GET /status` reflects both.
3. **NT-5 passes** — an invalid record is detected **before commit** (not persisted); replaying the same
   operation is **idempotent** (one row, same result); **lineage is complete** (queryable chain).
4. Existing **M11/M12/M13** tests stay green; **M14** build/typecheck stays green; no API contract changes;
   no fabricated real-data metrics; the **M11 MIXED** conclusion is untouched.
