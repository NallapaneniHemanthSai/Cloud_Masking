# ADR-0002 — Compute Environment

- **Status:** ACCEPTED (2026-08-06)
- **Milestone:** M1
- **Related:** Risk R-02, Assumption AS-04, AC-4 (frozen resource envelope)

## Context

Verified host environment (M1): macOS (Darwin 25.5.0), Python 3.14.2, **PyTorch 2.11.0 with `cuda=False`**
(no NVIDIA GPU). Apple Silicon **MPS** backend is the only hardware acceleration available. The project
requires training up to four segmentation architectures (U-Net, Attention U-Net, DeepLabV3+, optional
SegFormer) and comparing them under a **frozen resource envelope** (AC-4).

## Decision

1. **Train and evaluate on this Mac using device auto-detection:** prefer **CUDA → MPS → CPU** at runtime,
   selected via config (never hardcoded).
2. **Cap the resource envelope** for feasibility: bounded patch size (e.g. 256×256), curated CloudSEN12
   subset, gradient accumulation for effective batch size, mixed precision where MPS supports it.
3. Provide two config profiles:
   - **`smoke`** — tiny subset, few steps; used for tests/CI and quick correctness checks (runs anywhere).
   - **`full`** — the frozen AC-4 envelope used for all reported baseline-vs-candidate comparisons.
4. Keep the codebase **device-agnostic** so a `full` run can be exported to Colab/Kaggle/lab GPU without code
   changes (AS-04), should MPS prove too slow for DeepLabV3+.

## Consequences

- **Positive:** everything runs on the owner's laptop; reproducible on any machine via the same config; CI
  stays fast via the `smoke` profile.
- **Negative / to manage:** MPS is slower and has occasional op-coverage gaps vs CUDA; DeepLabV3+ training may
  be time-consuming (R-02). Mitigation: subset + accumulation + optional GPU export.
- **AC-4 obligation:** the exact `full` profile (versions, patch size, batch, steps, hardware) is frozen and
  recorded **before O2** and reused unchanged for the O3 comparison. Any change to the envelope invalidates
  the comparison and requires a documented re-baseline.

## Verification owed (M2)

Confirm MPS is actually used by a tiny training step; record throughput to size the `full` envelope realistically.
