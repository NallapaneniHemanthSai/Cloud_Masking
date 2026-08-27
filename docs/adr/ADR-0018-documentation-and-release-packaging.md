# ADR-0018 — Documentation & Release Packaging (D6)

- **Status:** ACCEPTED (2026-08-27)
- **Milestone:** M18 (Documentation)
- **Related:** ADR-0004 (Python runtime), ADR-0012 (dataset access), ADR-0013 (backend API),
  ADR-0014 (frontend), ADR-0016 (acceptance harness), ADR-0017 (deployment);
  `07_MILESTONE_PLAN.md` §M18 + **D6**, `01_REQUIREMENTS.md` (FR-6, NFR-5, §7 reproducibility),
  `06_KPI_ACCEPTANCE.md`; Objective **O5**.

## Objective

Deliver what the milestone plan defines for **M18 — Documentation**: *"README, API docs, architecture,
dataset guide, install, user manual, dev guide, deployment guide,"* with the exit criterion
**"Docs complete & consistent."** Together with M17 this closes **D6** — *repo package, manifest,
install/operating guide, API docs, reproducibility*.

The audience is a **new developer or an independent reviewer (O5)** who has the repository and nothing
else: no access to the build history, no conversation context, no author to ask.

## Context

M1–M17 produced a working system whose documentation grew **milestone-by-milestone** and was never
reconciled as a set. A read-only audit before implementation found genuine defects, not cosmetic ones:

- `README.md` still opened with *"Status: Milestone 2 (Project Scaffold) complete … no application
  logic, no installed dependencies, no datasets"* — false since M3, and the **first thing** a reviewer
  reads.
- `backend/README.md` still declared *"Milestone 2 status: scaffold only (no runtime logic; nothing
  installed)"* and told the reader **not** to run setup.
- Four of the eight artifacts the M18 row names — **install guide, user manual, developer guide, API
  docs** — did not exist at all.
- `01_REQUIREMENTS.md` FR-2 names `scripts/run_reference.sh` and `backend/evaluation/oracle.py` as the
  one-command reference path and independent oracle. **Neither exists.**

The last two matter for how M18 is scoped: documentation work must **report** the fourth item, not
quietly manufacture the missing scripts (that is M6–M9 scope and would be inventing evidence), and must
not restate the third as if it were done.

## Decision

### 1. Documentation is Markdown **in the repository** — no documentation site
The docs stay as `docs/<topic>/README.md`, the convention M3–M17 already established, with a new
`docs/README.md` index as the single entry point.

**Rejected:** MkDocs / Sphinx / Docusaurus. They would add a toolchain, a build step, CI, and a hosting
target to a project that is **graded and reviewed from the repository itself**. A generated site also
introduces a new way for docs to be stale (published site vs source). The opportunity cost is real and
the benefit is presentational only. Markdown renders in GitHub, in an editor, and offline, and it
diffs in review.

### 2. The API reference is **generated from the OpenAPI schema**, never hand-written
`backend/scripts/generate_api_docs.py` imports `app.main.create_app()`, takes `app.openapi()`, and
renders `docs/api/README.md`. **No running server is required** — the factory is imported directly, so
the generator works in CI and in a clean checkout.

Rationale: the single worst documentation defect this milestone found was **hand-written text drifting
from code** (`backend/README.md` describing a scaffold that had not existed for fifteen milestones). A
hand-maintained endpoint table would reproduce that failure the first time a field changes. Generating
from the schema makes the **code the single source of truth** and makes drift *detectable* rather than
invisible.

**Trade-off:** the generated page is structural (paths, methods, DTO fields, status codes) and cannot
explain *why* an endpoint exists. Narrative belongs in the user guide and ADRs, which link to it. The
generated file **is committed**, so a reader gets the reference without running anything.

### 3. "Complete & consistent" is made **executable**, not asserted
`backend/tests/test_documentation.py` checks the exit criterion mechanically: every required document
exists; every relative Markdown link resolves; every referenced ADR file exists; every script and
config path named in the docs exists; the stale "M2 scaffold" claims cannot come back; the KPI table
still reads **NOT YET MEASURED**; the M11 conclusion still reads **MIXED**.

Rationale: M1's `09_CONSISTENCY_AUDIT.md` was a *point-in-time* manual audit — accurate the day it was
written and progressively less true afterwards. Following the M16/M17 pattern, a claim the repository
makes about itself should be a claim the repository can **re-check on demand**. This turns "docs are
consistent" from a statement into a test that fails when it stops being true.

### 4. Documentation work does **not** touch application code
The only source change is a `DOCS_VERSION` constant in `app/core/constants.py` (the project's
established per-milestone version convention). No model, training, evaluation, failure-analysis,
degraded-mode, API, or frontend behaviour changes. M18 describes the system; it does not alter it.

### 5. Honest gaps are **recorded**, not closed
`docs/planning/10_DOCUMENTATION_AUDIT.md` records the M18 audit, including the FR-2 gap
(`run_reference.sh` / `oracle.py` never built) and the unmeasured-KPI position, with owning milestones.
Writing the missing scripts to make a checklist green would be fabricating M6–M9 deliverables inside a
documentation milestone.

### 6. Real-data KPI measurement is **NOT** in M18
The M18 row is *Documentation*; `06_KPI_ACCEPTANCE.md` states every KPI needs a real frozen-envelope
**AC-4** dataset that does not exist locally. `01_REQUIREMENTS.md` maps **O5 to M18–M20 jointly** and
tags **AC-1** with M18 — M18's obligation is therefore to **document the cross-region/season validation
path and its current status**, not to produce the measurement. All KPIs stay **NOT YET MEASURED**; the
M11 conclusion stays **MIXED**.

## Consequences

**Positive**
- A new developer can go from `git clone` to a running system by following one document, on either the
  host path or the Docker path, without prior context.
- The API reference cannot silently drift; regenerating is one command and a diff shows the change.
- Doc rot becomes a **test failure** instead of a discovery made by a reviewer.
- No new runtime dependency, no build step, no hosting.

**Negative / limitations**
- The generated API page reflects the schema at generation time; if someone changes a DTO and does not
  regenerate, the committed page is stale until the docs test flags the mismatch.
- The docs test checks *structural* consistency (existence, links, forbidden claims). It cannot verify
  that prose is **accurate** — that still needs human review.
- Screenshots of the UI are **DEFERRED**: they are large binaries that go stale on every style change,
  and the deployed stack renders the real thing in seconds.

## Honesty labels
Nothing in M18 measures anything. No REAL result is produced, promoted, or implied by documenting the
system. All formal KPIs remain **NOT YET MEASURED**, the bounded M11 real-data conclusion remains
**MIXED**, API/harness outputs remain **SYNTHETIC/DEMO**, and the FR-2 one-command reference path plus
independent oracle remain **NOT BUILT** (owned by M6–M9, recorded in the audit).
