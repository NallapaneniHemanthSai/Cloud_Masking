# Documentation Completeness & Consistency Audit (M18)

> **Milestone:** M18 (Documentation) · **Deliverable:** D6 · **Date:** 2026-08-27
> **Method:** read-only review of every planning document, ADR, guide and component README, plus an
> **executable** audit (`backend/tests/test_documentation.py`) that re-checks the mechanical parts on
> demand. Succeeds [`09_CONSISTENCY_AUDIT.md`](09_CONSISTENCY_AUDIT.md) (M1), which covered the
> planning set only.

---

## 1. Completeness — the artifacts M18 names

The milestone plan's M18 row names eight artifacts. Status **before** and **after** this milestone:

| # | Artifact | Before M18 | After M18 |
|---|----------|-----------|-----------|
| 1 | README | present but **factually wrong** (claimed M2 scaffold) | **FIXED** — `README.md` |
| 2 | API docs | **ABSENT** | **ADDED** — [`docs/api/README.md`](../api/README.md), generated from OpenAPI |
| 3 | Architecture | present | **UPDATED** — [`03_ARCHITECTURE.md`](03_ARCHITECTURE.md) |
| 4 | Dataset guide | present (M3/M12) | verified, linked |
| 5 | Install guide | **ABSENT** | **ADDED** — [`docs/install/`](../install/README.md) |
| 6 | User manual | **ABSENT** | **ADDED** — [`docs/user_guide/`](../user_guide/README.md) |
| 7 | Developer guide | **ABSENT** | **ADDED** — [`docs/developer_guide/`](../developer_guide/README.md) |
| 8 | Deployment guide | present (M17) | verified, linked |

**D6 additions:** [`docs/README.md`](../README.md) (index) and [`docs/MANIFEST.md`](../MANIFEST.md)
(package manifest, provenance, licences, evidence status, reproducibility).

**Verdict: COMPLETE.** Four of the eight named artifacts did not exist before M18.

---

## 2. Defects found and fixed

| # | Defect | Severity | Where | Resolution |
|---|--------|----------|-------|------------|
| D-1 | `README.md` opened with *"Status: Milestone 2 (Project Scaffold) complete … no application logic, no installed dependencies, no datasets"* | **HIGH** — the first thing a reviewer reads, and false since M3 | `README.md:7` | Replaced with the real status + an up-front evidence statement |
| D-2 | `backend/README.md` declared *"Milestone 2 status: scaffold only (no runtime logic; nothing installed)"* and told the reader **not** to run setup | **HIGH** — actively misleads a new developer | `backend/README.md` | Rewritten for the delivered system |
| D-3 | Install guide, user manual, developer guide, API reference did not exist | **HIGH** — D6 incomplete; a reviewer could not install or operate the system from the repo alone | — | All four written |
| D-4 | No documentation entry point; 48 files with no index | **MEDIUM** | — | [`docs/README.md`](../README.md) added |
| D-5 | Consistency was asserted by a 2026-08-06 manual audit and never re-checked | **MEDIUM** | `09_CONSISTENCY_AUDIT.md` | Made executable — `backend/tests/test_documentation.py` |
| D-6 | `docs/planning/03_ARCHITECTURE.md` did not list ADR-0018 | **LOW** | — | Registered |

---

## 3. Open findings — recorded, deliberately **not** fixed by M18

These are genuine gaps. Closing them inside a documentation milestone would mean writing missing
engineering deliverables to make a checklist green, which is exactly the kind of fabrication this
project's honesty rules forbid.

| # | Finding | Owning milestone | Impact |
|---|---------|------------------|--------|
| **O-1** | `01_REQUIREMENTS.md` **FR-2** names `scripts/run_reference.sh` (one-command reference path) and `backend/evaluation/oracle.py` (independent expected-result oracle). **Neither was ever built.** | **M6–M9** | FR-2's validation method — "one-command run rebuilds baseline; oracle re-derives expected metrics independently" — **cannot currently be executed**. This weakens the O2 reproducibility claim and should be closed before any independent-acceptance (O5) sign-off. |
| **O-2** | Project licence is **"TBD (confirm at approval)"** in `backend/pyproject.toml` | Repository owner | Blocks public release / redistribution. |
| **O-3** | **A-01** KL deployment stakeholder and **A-03** independent O5 reviewer are still unnamed | Repository owner | A-01 blocks O4/O5 sign-off; A-03 is needed before M19. |
| **O-4** | All KPIs remain **NOT YET MEASURED**; AC-1/AC-3/AC-4 unmet | M19/M20 window | The Pass Contract is not yet satisfiable. The harness reports this honestly as `SAFETY_PASS_KPI_NOT_YET_MEASURED`. |
| **O-5** | `01_REQUIREMENTS.md` tags **AC-1** with M18 ("region/season stratified results") | M19/M20 | M18 is a *documentation* milestone; O5 spans **M18–M20 jointly**. M18 documents the cross-region/season validation path and its status; it does **not** produce the measurement. |

---

## 4. Consistency checks

Mechanical checks, all executed by `backend/tests/test_documentation.py`:

| # | Check | Result |
|---|-------|--------|
| 1 | Every required document exists | PASS |
| 2 | Every relative Markdown link resolves | PASS |
| 3 | Every referenced `ADR-NNNN` has a file | PASS |
| 4 | ADR numbering 0001–0018, gap only at 0005 (never issued) | PASS |
| 5 | Every script/test path named in a guide exists | PASS |
| 6 | Stale "M2 scaffold" claims absent from both READMEs | PASS |
| 7 | Generated API reference is marked generated and names its generator | PASS |
| 8 | API reference covers every route in the running app | PASS |
| 9 | KPI table still reports NOT YET MEASURED | PASS |
| 10 | M11 conclusion still MIXED wherever the comparison is discussed | PASS |
| 11 | No guide states a measured KPI value | PASS |
| 12 | All five honesty labels explained for the reader | PASS |
| 13 | Manifest records the unbuilt FR-2 components | PASS |
| 14 | NT-1..NT-5 still pass; KPI status unchanged | PASS |
| 15 | API surface unchanged by M18 (15 routes) | PASS |

Re-run at any time:

```bash
backend/.venv/bin/python backend/tests/test_documentation.py
backend/.venv/bin/python backend/scripts/generate_api_docs.py --check
```

---

## 5. Verdict

**M18 documentation is complete and consistent.** All eight named artifacts exist, D6's manifest and
reproducibility statement are in place, and consistency is enforced by a test rather than asserted by a
dated note.

Five open findings (§3) are recorded with owning milestones. **O-1 is the most consequential** — FR-2's
one-command reference path and independent oracle do not exist, so that requirement's stated validation
method cannot be run today. It belongs to M6–M9 and should be closed before independent acceptance.

No measurement was produced, promoted, or implied by this milestone.
