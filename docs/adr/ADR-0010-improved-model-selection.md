# ADR-0010 — Improved Model Selection

- **Status:** ACCEPTED (2026-08-12)
- **Milestone:** M10 (Improved Segmentation Model)
- **Related:** ADR-0006 (baseline U-Net), ADR-0002 (compute/MPS), ADR-0007 (training), ADR-0008/0009
  (evaluation/failure analysis), O3 (contribution), Risk R-02, R-15, R-16

## Decision

Adopt **Attention U-Net** (U-Net + additive attention gates on the skip connections) as the **improved**
architecture, alongside — not replacing — the baseline U-Net. It **reuses the existing model abstraction**
(`BaseSegmentationModel`, `ModelConfig`, `ModelRegistry`, `ModelFactory`) and shared building blocks, adds
a modest parameter overhead, is fully **CPU/MPS compatible**, and directly targets the improvement
hypothesis. **This milestone establishes the architecture + comparison infrastructure only — no
performance is claimed; real-data results remain NOT YET MEASURED.**

## Baseline limitation

The baseline U-Net fuses encoder skips by plain concatenation. On **thin cloud** and ambiguous
cloud-vs-bright-surface boundaries (the project's hardest cases, R-16), unfiltered skips can propagate
low-relevance features, and the model has limited ability to **emphasise the informative regions** of each
skip. M9 is built to expose exactly these per-class/thin-cloud failures.

## Improvement hypothesis (to be tested later, not assumed)

> *The baseline U-Net may be limited in how selectively it aggregates skip-connection features. Adding
> attention gates that re-weight skip features by relevance should improve difficult cloud classes
> (especially thin cloud) and boundary failure cases, without imposing unreasonable compute cost.*

This is a **hypothesis**. M10 builds the architecture + comparison harness; the answer awaits controlled
training (M7 engine) + evaluation (M8) + failure analysis (M9) in later milestones.

## Candidate architectures evaluated

Scored 1–5 (higher better) against the required criteria on the frozen MPS/CPU envelope (ADR-0002).

| Criterion | U-Net (baseline) | **Attention U-Net (selected)** | UNet++ | DeepLabV3+ | SegFormer |
|-----------|:---:|:---:|:---:|:---:|:---:|
| 1. Segmentation quality (typical) | 3 | 4 | 4 | 4 | 5 |
| 2. Thin-cloud focus mechanism | 2 | **4** | 3 | 3 | 4 |
| 3. Thick-cloud | 4 | 4 | 4 | 4 | 4 |
| 4. Cloud-shadow | 3 | 4 | 4 | 3 | 4 |
| 5. Boundary/failure behaviour | 3 | 4 | 4 | 3 | 4 |
| 6. Parameter count (smaller better) | 5 | **4** | 3 | 2 | 2 |
| 7. Memory (MPS) | 5 | **4** | 2 | 2 | 2 |
| 8. MPS/CPU compatibility | 5 | **5** | 5 | 4 | 3 |
| 9. Implementation complexity (simpler better) | 5 | **4** | 3 | 2 | 2 |
| 10. Training cost (lower better) | 5 | **4** | 3 | 2 | 1 |
| 11. Reproducibility | 5 | **5** | 4 | 3 | 3 |

## Selection criteria & compute constraints

Selection weighted **thin-cloud mechanism (2), MPS memory (7), MPS compatibility (8), implementation
complexity (9), training cost (10), reproducibility (11)** heavily, because the improved model must run
reproducibly on the frozen Apple-Silicon envelope (no CUDA, capped patch size — ADR-0002). We deliberately
**do not** pick the most sophisticated option.

## Parameter budget

Attention U-Net adds three 1×1 convolutions per decoder stage (gate: `W_g`, `W_x`, `ψ`), a **small**
overhead over U-Net (typically < ~10–15% more parameters at the same width/depth). The exact counts are
**MEASURED** per config by the comparison harness (`profile_architecture`), not asserted here.

## Expected benefit

Attention gates suppress irrelevant skip activations and highlight regions relevant to the decoder's
current scale — the mechanism most directly aimed at **thin-cloud / bright-surface discrimination** (O3).
Whether it *actually* helps is an empirical question for later milestones.

## Selected architecture

**Attention U-Net** (`name="attention_unet"`), sharing the U-Net encoder/`ConvBlock`/head via a common
`app.models.blocks` module; the decoder replaces plain skip concatenation with an attention gate.

## Alternatives rejected

- **DeepLabV3+** — strong multi-scale context, but heavier and typically relies on ImageNet-pretrained RGB
  backbones that mismatch 13-band input; higher memory/training cost on MPS. **Kept as a future comparison
  model (M11).**
- **UNet++** — dense nested skips improve boundaries but cost significant memory; complexity not justified
  as the *first* improved model.
- **SegFormer** — excellent accuracy but transformer training is data/compute-hungry and has weaker MPS op
  coverage; marked OPTIONAL in the overall plan.

## Trade-offs

Attention U-Net trades a small parameter/compute increase for a targeted relevance-weighting mechanism,
while remaining simple, reproducible, and MPS-friendly — the right first step over the baseline. It may
help less than a heavier context model on some classes; that is acceptable for a controlled, low-risk
comparison.

## Consequences

`app.models` gains a shared `blocks` module (U-Net refactored to use it — behaviour unchanged), an
`attention_unet` architecture registered alongside `unet`, an improvement-mechanism metadata field, an
`IMPROVED_MODEL_VERSION`, and typed **architecture-comparison** records + a `model_compare` CLI. Training
(M7), evaluation (M8), and failure analysis (M9) are **unchanged**.

## Experiment design (for later milestones)

Under the **frozen AC-4 envelope**: train U-Net and Attention U-Net with the **same** data/config/seed;
evaluate with M8 (per-class + stratified, esp. **thin cloud**); analyse failures with M9; compare params +
metrics with the M10 comparison records. A meaningful improvement must show **per-class (thin-cloud) gains
at a reasonable compute cost**, not just a higher aggregate.

## Failure modes

Attention gates can be under-trained on tiny datasets; may not help if the bottleneck is data/label
quality (R-17) rather than skip selection; extra parameters slightly increase overfitting risk on small
subsets (mitigated by dropout/weighting available in training). If it shows **no** benefit at equal cost,
the honest conclusion is "no improvement" — the harness supports a negative result.

## Future improvements

DeepLabV3+ / UNet++ as additional comparison models (M11); spectral-index input channels; boundary-aware
losses; FLOP measurement via a profiler once a reliable, dependency-light method is chosen (currently
DEFERRED).
