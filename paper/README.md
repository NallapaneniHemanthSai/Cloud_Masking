# Paper / Research (D7)

**Milestone 19 deliverables.** Research write-up for *Cloud Masking Across Thin Cloud, Haze, Snow and
Bright Surfaces*. Evidence policy: [ADR-0019](../docs/adr/ADR-0019-research-paper-and-evidence-policy.md).

| Document | Contents |
|---|---|
| [00_RESEARCH_PAPER.md](00_RESEARCH_PAPER.md) | The paper draft — problem, method, results, limitations, conclusion (19 sections) |
| [01_LITERATURE_REVIEW.md](01_LITERATURE_REVIEW.md) | 11 verified sources: citation · task · method · relevance · limitation |
| [02_COMPARISON_TABLE.md](02_COMPARISON_TABLE.md) | U-Net vs Attention U-Net — mechanism, cost, measured results, unmeasured cells labelled |
| [03_ABLATION_TEMPLATE.md](03_ABLATION_TEMPLATE.md) | 8 ablation dimensions, fully specified — **all NOT EXECUTED** |
| [04_RESULTS.md](04_RESULTS.md) | The M11 measured evidence, transcribed with provenance |
| [references.bib](references.bib) | BibTeX; every entry verified against Crossref / arXiv |

## The result, stated correctly

> On a bounded 32-sample expert-labelled CloudSEN12+ subset (3 seeds), Attention U-Net improved
> **thin-cloud IoU in all 3 seeds (mean +0.050)** at **×1.012** parameters, and regressed
> **cloud-shadow IoU in all 3 seeds (mean −0.018)**. The decision framework returned IMPROVED for one
> seed and REGRESSION for two. **Overall verdict: MIXED.**

**This is not "Attention U-Net is better."** That claim is unsupported and must not appear in any
summary, slide, or abstract derived from this work.

## What M19 did not produce

M19 is a write-up milestone. It ran **no new experiment** and produced **no new measurement**.

| | |
|---|---|
| Formal KPIs (KPI-1..6, KPI-E1..E7) | **NOT YET MEASURED** |
| AC-1 / AC-3 / AC-4 | **NOT YET MEASURED** |
| All ablations | **NOT EXECUTED** |
| Comparison vs published methods | **NOT EXECUTED** |
| FR-2 `run_reference.sh` + `evaluation/oracle.py` | **NOT BUILT** → independent reference validation **NOT EXECUTABLE** (O5 blocker) |

## Verification

```bash
backend/.venv/bin/python backend/tests/test_paper.py
```

Checks that every `\cite` key resolves to `references.bib`, that no forbidden claim ("Attention U-Net is
better", fabricated significance) appears, that MIXED is preserved, that every ablation is labelled
NOT EXECUTED, and that the transcribed M11 numbers match the M11 source record exactly.
