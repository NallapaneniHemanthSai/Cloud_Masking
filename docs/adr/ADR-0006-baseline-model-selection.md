# ADR-0006 — Baseline Segmentation Model Selection

- **Status:** ACCEPTED (2026-08-10)
- **Milestone:** M6 (Baseline Model)
- **Related:** ADR-0001 (datasets), ADR-0002 (compute), O1 (baseline), O2 (reference), Risk R-02/R-16

## Decision

Adopt a **standard 2-D U-Net** (encoder / decoder / head) as the **baseline** segmentation architecture
for multi-class cloud masking. It is implemented as a reusable, configurable module
(`app.models.unet.UNet`) that plugs into training (M7) and inference (M13) without modification.

## Context

- The baseline (O1) must establish a defensible reference before the O3 contribution (cloud-vs-bright-
  surface discrimination). It should be **simple, well-understood, and cheap to train** on the frozen
  Apple-Silicon (MPS) envelope (ADR-0002, Risk R-02).
- Inputs are multi-spectral (13-band CloudSEN12 L1C / 4-band On Cloud N); outputs are per-pixel class
  logits (4 classes for CloudSEN12).
- Class imbalance (thin cloud) is a known risk (R-16); the baseline must be a fair, reproducible starting
  point, not a tuned champion.

## Alternatives considered

| Architecture | Summary | Pros | Cons (for a baseline here) |
|--------------|---------|------|----------------------------|
| **U-Net** *(selected)* | Symmetric encoder/decoder with skip connections. | Simple, robust, low-parameter, fast to train, ubiquitous cloud-masking baseline; easy to reason about and reproduce. | Plain skips can under-segment thin/ambiguous boundaries. |
| **Attention U-Net** | U-Net + attention gates on skips. | Better focus on relevant regions (helps thin cloud/edges). | More parameters/compute; better suited as an **O3 contribution** (M10), not the baseline. |
| **UNet++** | Nested/dense skip pathways. | Strong boundary accuracy. | Heavier memory/compute; complexity not justified for a baseline on MPS. |
| **DeepLabV3+** | Atrous/ASPP encoder + decoder, typically a pretrained backbone. | Excellent multi-scale context. | Heavier; benefits from ImageNet-pretrained RGB backbones that don't match 13-band input; better as a **comparison model** (M10–M11). |
| **SegFormer** | Transformer (MiT) encoder + light MLP decoder. | Strong accuracy, global context. | Data/compute hungry; transformer training on MPS with a small curated subset is impractical for a baseline (marked OPTIONAL overall). |

## Trade-offs

- **Simplicity vs. accuracy:** U-Net trades peak accuracy for reproducibility, low compute, and clarity —
  the right trade for a *baseline* whose job is to be a fair reference (AC-4 frozen envelope).
- **Parameters vs. memory:** configurable `base_channels`/`encoder_depth` let us cap parameters to fit MPS
  memory; larger variants remain available.
- **Pretraining:** avoiding pretrained RGB backbones sidesteps the band-mismatch problem of 13-band input.

## Why U-Net was selected

1. It is the **canonical, defensible baseline** for satellite cloud segmentation.
2. It is **cheap and fast** on the frozen MPS envelope (ADR-0002), enabling reproducible runs (R-02).
3. It handles **arbitrary input channels** (13-band) natively — no pretraining/band mismatch.
4. Its **encoder/decoder/head** separation makes the more advanced O3 candidates (Attention U-Net,
   DeepLabV3+) drop-in successors reusing the same abstractions.

## Consequences

- The `app.models` package exposes `ModelConfig`, `ModelRegistry`, `ModelFactory`, `BaseSegmentationModel`,
  and `UNet`, plus checkpoint/experiment metadata — reusable by training (M7) and inference (M13).
- PyTorch is a **guarded** dependency; the package imports without it and errors clearly on model build.
- The baseline provides the O1 result and the substrate for the O2 reference (M7–M9).

## Future improvements

- **M10 (O3 contribution):** Attention U-Net and DeepLabV3+ as improved models, compared under AC-4.
- Optional **SegFormer** if compute/time permit (spec-marked optional).
- Add spectral-index input channels (NDSI, cirrus) and class-imbalance-aware sampling (R-16) at training.
- Deep supervision / boundary-aware heads for thin-cloud edges.
