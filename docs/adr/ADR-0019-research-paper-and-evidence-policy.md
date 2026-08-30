# ADR-0019 — Research Paper Structure & Evidence Policy (D7)

- **Status:** ACCEPTED (2026-08-27)
- **Milestone:** M19 (Research paper)
- **Related:** ADR-0001 (dataset selection), ADR-0003 (OSCD, deferred), ADR-0008 (evaluation),
  ADR-0009 (failure analysis), ADR-0010 (Attention U-Net hypothesis), ADR-0011 (controlled comparison
  + decision framework), ADR-0012 (experimental dataset), ADR-0016 (acceptance harness),
  ADR-0018 (documentation); `07_MILESTONE_PLAN.md` §M19 + **D7**; Objective **O5**.

## Objective

Produce the M19 deliverables the milestone plan names — *literature review, citations/references,
comparison table, ablation template, results write-up* — as a **paper draft**, and do so under an
evidence policy strict enough that an independent reviewer (O5) can check every claim.

## The problem this ADR exists to prevent

A research write-up is the single highest-risk artifact in this project. Every earlier milestone
produced evidence with an explicit status label; a paper is where those labels are most likely to be
quietly dropped, because prose rewards confident, uniform claims. The specific failure modes:

- A **hypothesis** (ADR-0010: "attention gates should improve thin cloud") reappearing in a results
  section as a finding.
- **SYNTHETIC** pipeline-validation numbers being cited as model performance.
- The M11 verdict — *thin cloud improved, cloud shadow regressed, verdict* **MIXED** — being compressed
  into "Attention U-Net performs better", which the evidence does **not** support.
- Empty comparison or ablation cells being filled with plausible numbers so a table looks complete.
- **NOT YET MEASURED** KPIs appearing as measured because a table needs a value.

## Decision

### 1. A three-level evidence hierarchy, applied to every claim
Every substantive sentence in the paper is one of exactly three kinds, and the kind is explicit:

| Kind | Definition | How it is written |
|------|------------|-------------------|
| **SOURCE-DERIVED FACT** | Comes from a cited external publication | Stated with its citation key; never extended beyond what the source shows |
| **PROJECT RESULT** | Measured by this project's own runs | Carries a status label and points to the artifact it came from |
| **INTERPRETATION** | Our reading of the above | Explicitly marked as interpretation, and separated from the result it interprets |

An interpretation may never be promoted to a result by being placed next to one.

### 2. Status labels are mandatory and non-substitutable
`REAL — BOUNDED M11 EXPERIMENT` · `SYNTHETIC` · `DEMO` · `PLANNED / NOT EXECUTED` · `DEFERRED` ·
`NOT YET MEASURED` · `NOT BUILT`. A missing number is written as its label. **An empty cell is a
finding, not a gap to be filled.**

### 3. The M11 conclusion is transcribed, not re-derived
The paper **quotes** the M11 verdict and its per-seed numbers from
`docs/comparison/real_experiment_cloudsen12.md`; it does not recompute, re-weight, or re-interpret
them. The verdict stays **MIXED**, including the fact that the decision framework *flips across seeds*
(seed 1 IMPROVED; seeds 2 and 3 REGRESSION). Reporting only the thin-cloud gain would be selective
reporting; reporting only the seed-dependence would understate a real, consistent effect. Both go in.

### 4. Literature is selected by primary-source rule
Cited works must be **peer-reviewed publications, official dataset papers, or archival preprints of
record**. No blogs, no vendor pages, no secondary summaries as scientific evidence. Every citation's
metadata is verified against **Crossref** (or the **arXiv API** for preprints) rather than written from
memory — the failure mode being a plausible-looking but wrong volume, year, or author list. Each entry
records: citation · task · method · relevance to this project · limitation.

### 5. Ablations are a template, not a table of results
The project has run **one** controlled experiment (M11, 3 seeds). Every ablation dimension is therefore
specified — hypothesis, factor levels, fixed controls, metric, how it would be executed — and marked
**NOT EXECUTED**. A template that is honestly empty is a contribution; a fabricated ablation table is
misconduct.

### 6. Statistical claims are bounded by what n=3 supports
No confidence intervals, no significance tests, no error bars beyond the descriptive spread already
recorded (mean ± population SD over 3 seeds). ADR-0011 already fixes that fewer than two seeds ⇒
`NOT_MEASURED`; three seeds support a **consistency** claim ("improves in all 3 seeds") but **not** a
significance claim. The paper says so explicitly.

### 7. The paper does not close engineering gaps
FR-2's `scripts/run_reference.sh` and `backend/evaluation/oracle.py` remain **NOT BUILT**, so
independent reference validation is **NOT EXECUTABLE**. The paper reports this as a reproducibility
limitation and an O5 blocker. Writing those scripts inside a paper milestone would be scope-jumping,
and *describing* them as if they existed would be fabrication.

### 8. Claim legitimacy test
A claim may appear in the paper only if it passes all four:
1. It is traceable to a cited source, a recorded project artifact, or is labelled INTERPRETATION.
2. Its evidence status label is present and correct.
3. It does not generalise beyond the bounded subset (32 samples, 1 config, 12 epochs, 3 seeds).
4. It would survive a reviewer opening the referenced artifact.

## Alternatives considered

- **Write a conventional paper with a complete results table.** Rejected: the project has one bounded
  experiment and no AC-4 benchmark. A conventional table could only be completed by inventing numbers.
- **Report only the positive thin-cloud finding.** Rejected: selective reporting. The cloud-shadow
  regression is part of the same measurement and is what makes the verdict MIXED.
- **Defer the paper until real KPIs exist.** Rejected: M19's exit criterion is *"paper draft complete,"*
  and the honest draft — including a precise account of what is not yet measured — is itself the
  deliverable and the clearest specification of what the remaining experiments must produce.
- **Cite from memory and tidy references later.** Rejected: unverifiable citations are the easiest way
  to lose a reviewer's trust in everything else.

## Consequences

**Positive** — Every claim is checkable; the paper doubles as a precise statement of what remains
unmeasured; citation metadata is machine-verified; a reader cannot mistake synthetic for real.

**Negative** — The paper reads as more provisional than a conventional draft, with visible empty cells
and repeated labels. That is the intended cost: the alternative is a document that looks finished and
is not trustworthy.

## Honesty labels
M19 produces **no new measurement**. All formal KPIs remain **NOT YET MEASURED**; the M11 real-data
conclusion remains **MIXED**; all ablations are **NOT EXECUTED**; FR-2 reference/oracle remain
**NOT BUILT**.
