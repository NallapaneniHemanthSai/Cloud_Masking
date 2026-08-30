# U-Net vs Attention U-Net — Comparison Table

**Milestone 19 · Deliverable D7.** Measured values transcribed from
[`04_RESULTS.md`](04_RESULTS.md) / the M11 record. Unavailable values carry a status label —
**no cell is filled with an estimate** (ADR-0019 §2).

Configuration for all measured values: `encoder_depth=3, base_channels=16, in_channels=13,
num_classes=4, patch=128`, batch 8, 12 epochs, AdamW + cosine, cross-entropy, device MPS, 3 seeds,
32-sample expert-labelled CloudSEN12+ subset.

---

## 1. Architecture and mechanism

| Property | U-Net (baseline) | Attention U-Net (improved) |
|---|---|---|
| Origin | Ronneberger et al., MICCAI 2015 | Oktay et al., MIDL 2018 |
| Project ADR | [ADR-0006](../docs/adr/ADR-0006-baseline-model-selection.md) | [ADR-0010](../docs/adr/ADR-0010-improved-model-selection.md) |
| Encoder / decoder | Symmetric contracting / expanding | **Identical** to baseline |
| Skip connection | Plain **concatenation**, unweighted | Concatenation **after an additive attention gate** |
| Gate internals | — | 3 × 1×1 convolutions per decoder stage (`W_g`, `W_x`, `ψ`) |
| What the gate does | — | Re-weights encoder features by relevance, conditioned on the decoder signal, before fusion |
| Shared code | `app/models/blocks.py` | **Same blocks** — only the skip path differs |

**Design note:** the two arms share every component except the skip path. That is what makes the M11
comparison attributable: any measured difference is caused by the attention gate, not by an incidental
difference in capacity, data, or schedule.

## 2. Cost

| Property | U-Net | Attention U-Net | Ratio | Status |
|---|---:|---:|---:|---|
| Parameters | **484,228** | **490,005** | **×1.012** | REAL — measured; independently re-derived in M19 |
| Training time | 1.00× | **×1.2–1.3** | — | REAL — measured |
| Output shape | `(N, 4, 128, 128)` | `(N, 4, 128, 128)` | identical | REAL |
| Inference latency | NOT YET MEASURED | NOT YET MEASURED | — | KPI-E5 unmeasured |
| Peak memory | NOT YET MEASURED | NOT YET MEASURED | — | KPI-E6 unmeasured |
| FLOPs | DEFERRED | DEFERRED | — | never instrumented (M10) |

**INTERPRETATION:** a +1.2% parameter cost is negligible; the ×1.2–1.3 training-time cost is the real
overhead, and it is a *training* cost, not necessarily an inference cost — inference latency is
unmeasured, so no deployment-cost claim is made.

## 3. Measured performance (REAL — BOUNDED M11 EXPERIMENT, 3 seeds)

Mean ΔIoU (improved − baseline) across seeds, with per-seed consistency:

| Class | Mean ΔIoU | Consistent across seeds? | Supports a directional claim? |
|---|:---:|:---:|---|
| **thin_cloud (primary)** | **+0.050** | **yes — 3/3 positive** | **yes** |
| cloud_shadow | −0.018 | **yes — 3/3 negative** | **yes** |
| thick_cloud | +0.031 | no (−0.057 … +0.122) | no |
| clear | +0.000 | no (−0.024 … +0.039) | no |
| macro IoU | +0.016 | no (−0.009 … +0.042) | no |

Thin-cloud detail (all REAL): IoU 0.4605→0.5073, 0.4402→0.5158, 0.5244→0.5520; recall +0.079 / +0.149 /
+0.111; false negatives −27,394 / −51,569 / −38,478.

| Framework verdict | Seed 1 | Seed 2 | Seed 3 | Overall |
|---|:---:|:---:|:---:|:---:|
| [ADR-0011](../docs/adr/ADR-0011-model-comparison.md) decision | IMPROVED | REGRESSION | REGRESSION | **MIXED** |

## 4. Hypothesis vs outcome

| | |
|---|---|
| **Hypothesis** (ADR-0010, pre-registered before any run) | Attention gates that re-weight skip features by relevance should improve difficult cloud classes — **especially thin cloud** — and boundary cases, without unreasonable compute cost. |
| **Thin cloud** | **Supported on this bounded subset** — +0.050 mean IoU, improves 3/3 seeds, recall and FN better every seed. |
| **Compute cost** | **Supported** — ×1.012 parameters, ×1.2–1.3 training time. |
| **Boundary / edge cases** | **NOT MEASURED** — spatial connected-component failure analysis is DEFERRED, so the boundary half of the hypothesis was never tested. |
| **Other difficult classes** | **Not supported** — cloud shadow regresses 3/3 seeds. |
| **Overall** | **MIXED.** The hypothesis is supported for its primary target and contradicted for another difficult class. |

## 5. Engineering properties

| Property | U-Net | Attention U-Net |
|---|---|---|
| MPS compatible | yes (verified — trained on MPS) | yes (verified — trained on MPS) |
| CUDA required | no | no |
| Deterministic seeding | yes (M7 `seed.py`) | yes (same path) |
| Config hash recorded | yes | yes |
| Registered in `ModelRegistry` | `unet` | `attention_unet` |
| Serving via `/models`, `/train`, `/predict` | yes | yes |
| Added infrastructure | — | **none** — reuses M6 abstraction, M7 trainer, M8 evaluation, M9 failure analysis |

## 6. Comparison against published methods

| Comparison | Status |
|---|---|
| vs Fmask / Fmask 4.0 | **NOT EXECUTED** |
| vs GCDB-UNet | **NOT EXECUTED** |
| vs CloudSEN12 published algorithm outputs | **NOT EXECUTED** |
| vs any leaderboard | **NOT EXECUTED** |

No external baseline was run. The M11 experiment compares **our** two arms on **our** subset under
identical conditions; it establishes nothing about how either compares to the literature.

## 7. Reading this table honestly

The defensible summary is:

> On a bounded 32-sample expert-labelled CloudSEN12+ subset, adding additive attention gates to U-Net's
> skip connections produced a **consistent thin-cloud improvement** (mean IoU +0.050, 3/3 seeds) at
> negligible parameter cost, alongside a **consistent small cloud-shadow regression** (mean −0.018,
> 3/3 seeds) on a class where both models are weak (IoU ≈ 0.1). The overall verdict is **MIXED**.

The following are **not** supported and must not be written: "Attention U-Net outperforms U-Net";
"attention improves cloud segmentation"; any statement of statistical significance; any comparison to
published methods; any claim about inference cost.
