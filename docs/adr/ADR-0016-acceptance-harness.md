# ADR-0016 — Guardrails & Acceptance Harness (D5)

- **Status:** ACCEPTED (2026-08-26)
- **Milestone:** M16 (Testing)
- **Related:** ADR-0008/0009 (evaluation/failure), ADR-0015 (integration/degraded/recovery/NT-5);
  `06_KPI_ACCEPTANCE.md` (AC-1..4, KPI table, **NT-1..NT-5**, Pass Contract), `01_REQUIREMENTS.md`
  (FR-7, NFR-2), Objective O5; milestone plan §M16 / Deliverable **D5**.

## Purpose

Deliver **D5 — the acceptance harness** that covers AC-1..4, all KPIs, and **all five mandatory negative
tests (NT-1..NT-5)**. Its job is not "more tests" but to **prove the project's safety/acceptance
properties**: every guardrail holds, every NT is detected (never silently passes), valid cases do not
falsely trigger, degraded-mode + recovery behave, and NT-5 lineage/idempotency hold — while **honestly**
reporting that the real-data KPI/AC-4 acceptance remains **NOT YET MEASURED**. It **reuses** M8 evaluation,
M9 failure analysis, and the M15 degraded/recovery/lineage infrastructure — no duplicate metric or
degraded-mode system.

## NT requirements (verbatim from the acceptance doc)

- **NT-1** — *overall accuracy dominated by easy pixels*: detect; abstain/degraded; label; prevent silent
  use. **Mechanism reused from M15** (`check_aggregate_hides_subgroup`).
- **NT-2** — *snow masked as cloud*: detect/abstain/label/prevent (+ recovery). Snow is labelled `clear`
  (class 0); the condition is **true-`clear` pixels predicted as cloud**. **New guardrail** over the M8
  confusion matrix.
- **NT-3** — *thin cloud leaking into analysis*: same. The condition is **true-`thin_cloud` predicted as
  `clear`** (leaks into the "usable/clear" analysis). **New guardrail** over the M8 confusion.
- **NT-4** — *a map hides uncertainty, missing coverage, or unsuitable resolution*: surface
  uncertainty/coverage/resolution; do not present a misleading map. **New guardrail** over map metadata
  (a map claiming a REAL overlay without uncertainty/coverage/resolution evidence is a violation).
- **NT-5** — *field/authoritative observations do not support the inference*: detect the invalid record
  **before silent commit**; replay is idempotent; lineage remains complete. **Mechanism reused from M15**
  (`lineage_service`).

## Violation vs pass

A guardrail **violation** is a detection: the harness runs a *negative* (bad-condition) fixture and the
guardrail **must** flag it (with requirement / observed / expected / evidence / action). An NT **passes
acceptance** only when BOTH hold: (a) the negative fixture is **detected** (and the system enters degraded
mode + recovers, or — for NT-5 — the invalid record is rejected before commit), and (b) the *positive*
(healthy) fixture does **not** falsely trigger. This prevents both silent-pass and false-alarm failure
modes.

## Aggregate-vs-subgroup / invalid-record / idempotency / lineage / degraded / recovery

- **Aggregate hides subgroup (NT-1):** reuse M15's guardrail (high pixel accuracy but weak thin-cloud /
  worst-class IoU).
- **Invalid record (NT-5):** reuse `idempotent_get_or_create` — validate **before** any write; invalid ⇒
  `GuardrailViolation`, nothing persisted.
- **Idempotent replay (NT-5):** the same operation keyed by `stable_hash` returns the existing row.
- **Lineage (NT-5):** `record_lineage`/`get_chain` — a complete, queryable chain.
- **Degraded mode / recovery:** on any NT-1..4 detection the harness calls M15 `enter_degraded` (persists
  labelled evidence, holds from silent use) and demonstrates `recover` (recovery log; `system_status`).

## Deterministic execution & fixture strategy

All fixtures are **deterministic, synthetic** (fixed confusion matrices / records / map metadata / invalid
records), explicitly labelled `SYNTHETIC`. Given fixed fixtures the `AcceptanceReport` content hash is
stable (timestamps excluded). No randomness, no network, no torch required.

## Synthetic vs real-data boundary

The harness proves the **safety properties on synthetic fixtures** (labelled `SYNTHETIC`). It **does not**
compute or fabricate real KPI values: the KPI/AC-4 rows are reported as **NOT YET MEASURED** (blocked on a
real AC-4 dataset). The overall verdict therefore separates **SAFETY = PASS** from **KPI ACCEPTANCE = NOT
YET MEASURED**; the project is not declared fully accepted while KPIs are unmeasured (honest to the Pass
Contract).

## Reporting format

A typed `AcceptanceReport` → JSON + Markdown (reusing the M5 `Report` model), with per-NT rows
(requirement / observed / expected / passed / evidence / action), the AC coverage, the KPI status table
(NOT YET MEASURED), a **coverage/test-inventory** matrix, `acceptance_version`, config hash, content hash,
and timestamp.

## CI / local execution

A CLI `run_acceptance.py` runs the harness from a clean checkout on `backend/.venv/bin/python`, writes the
reports, prints a per-NT summary, and **exits non-zero** if any NT fails or falsely triggers (so it can gate
CI). A thin `GET /acceptance` endpoint + an additive frontend **Acceptance** page surface the result in the
operable system (reusing M13/M14 patterns). Line-coverage % via `pytest-cov` is **not installed** and is
**deferred**; the harness instead reports a structured coverage/test-inventory matrix (which NT/AC/KPI each
test covers + the manual-harness counts).

## Limitations

Safety properties are proven on synthetic fixtures, not real data; NT-2/NT-3 detection is
confusion-matrix-based (pixel-level, no spatial connected-component analysis — consistent with M9's DEFERRED
spatial categories); KPI/AC-4 acceptance is NOT YET MEASURED; `pytest-cov` line-coverage is deferred.

## Deferred

Real AC-4 KPI measurement (needs a real frozen-envelope dataset); Docker/compose packaging + clean-env
rebuild (**M17**); `pytest`/`pytest-cov` install for line coverage; spatial (connected-component) NT-2/NT-3
refinements.

## Acceptance criteria

1. Every NT-1..NT-5 has a **deterministic pass fixture and fail fixture**; the fail fixture is detected, the
   pass fixture does not falsely trigger.
2. NT-1..4 detections drive **degraded mode + recovery** (reusing M15); NT-5 enforces
   detect-before-commit + idempotent replay + complete lineage.
3. The harness produces a structured JSON+MD `AcceptanceReport`, is **deterministic** (stable content hash),
   and the CLI **exits non-zero** on any failure.
4. KPI/AC-4 acceptance is reported **NOT YET MEASURED** (never fabricated); the M11 **MIXED** conclusion is
   untouched.
5. Existing **M11/M12/M13/M15** tests stay green; **M14** build/typecheck stays green; no existing guardrail
   is weakened; no M17 deployment work is pulled in.
