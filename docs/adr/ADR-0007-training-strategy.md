# ADR-0007 — Training Strategy

- **Status:** ACCEPTED (2026-08-10)
- **Milestone:** M7 (Training Engine)
- **Related:** ADR-0002 (compute/MPS), ADR-0006 (baseline model), O1/O2, Risks R-02, R-09, R-15, R-16

## Decision

Build a **custom, configuration-driven PyTorch `Trainer`** with pluggable optimizer / scheduler / loss, a
callback framework, a checkpoint manager, structured JSON/CSV logging, and deterministic seeding. The
trainer is **decoupled from evaluation and deployment** so Milestone 8 (evaluation) and later milestones
plug in via callbacks / an optional `metrics_fn` without architectural change. No third-party training
framework is adopted.

## Context

- Training must run on the frozen **Apple-Silicon (MPS) / CPU** envelope (ADR-0002) and consume the
  Milestone 6 models via `ModelFactory`.
- Reproducibility is a first-class requirement (R-09): fixed seeds, environment capture, versioned config.
- The engine must be **explainable** (project rule) and light (no heavy opaque dependencies).
- Evaluation metrics, benchmark comparisons, and deployment are explicitly **out of scope** for M7.

## Alternatives considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Custom minimal trainer** *(selected)* | Full control, explainable, light, MPS-friendly, decoupled from eval/deploy. | More code to write/maintain. | **Selected** — matches project's explainability + reproducibility rules. |
| PyTorch Lightning | Less boilerplate, many features. | Heavy/opaque, imposes structure, harder to reason about on MPS; couples to its abstractions. | Rejected. |
| Ignite / Accelerate | Lighter than Lightning, useful engines. | Extra dependency + abstractions; still less transparent than a small custom loop. | Rejected. |

## Optimizer selection

Configurable via `OptimizerConfig(name, lr, weight_decay, momentum, params)`; registry supports **Adam**,
**AdamW** *(default)*, **SGD**. AdamW is the default (decoupled weight decay, robust for segmentation). No
optimizer is hardcoded — selection is configuration-only.

## Learning-rate scheduler selection

Configurable via `SchedulerConfig(name, params)`; registry supports **CosineAnnealingLR** *(default)*,
**StepLR**, **ReduceLROnPlateau**. `ReduceLROnPlateau` steps on the monitored metric; others step per
epoch. Scheduler is optional (`None` = constant LR).

## Checkpoint strategy

`CheckpointManager` writes, per checkpoint: model/optimizer/scheduler `state_dict`s (weights **may** be
saved) **plus** a JSON metadata sidecar (`CheckpointState`). Policy: **best** (by monitored value) and
**latest**, with optional periodic `save_every`. Resume reads the sidecar (`CheckpointState`) + payload.
Evaluation metrics, if ever attached, are **optional metadata only** — never computed here.

## Early-stopping strategy

`EarlyStoppingCallback` monitors a configured value (default: `train_loss`, mode `min`) with `patience`
and `min_delta`; on no-improvement it sets `state.stop_requested`, which the trainer honours between
epochs. Independent of the trainer (a callback).

## Mixed-precision decision

AMP is **opt-in** and only enabled on **CUDA** (autocast + GradScaler). On **MPS/CPU it is disabled** by
default — AMP support is limited/unstable there (ADR-0002). Controlled by `mixed_precision` in config.

## Gradient-accumulation decision

Configurable `grad_accum_steps` (default 1) to reach an effective batch size larger than MPS memory
allows (ADR-0002). Loss is divided by the accumulation count; optimizer steps every N micro-batches.

## Random-seed strategy

A single `seed` seeds Python `random`, NumPy, and PyTorch (CPU + CUDA). `deterministic=True` additionally
requests `torch.use_deterministic_algorithms(warn_only=True)` and disables cuDNN benchmarking. DataLoader
worker seeding is provided via a seed-worker helper. The seed and environment are captured in
`TrainingMetadata` for reproducibility (R-09).

## Logging strategy

Structured logging via a `MetricSink` **abstraction** (`JsonlSink`, `CsvSink`, `ConsoleSink`) composed by
`TrainingLogger`. **JSON (JSONL) and CSV** are implemented. **TensorBoard is NOT integrated** — but the
`MetricSink` interface isolates it so a `TensorBoardSink` can be added later without touching the trainer.

## Experiment directory structure

```
outputs/experiments/<experiment_id>/
├── config.json         # serialized TrainingConfig
├── run.json            # serialized ExperimentRun (metadata, versions, refs)
├── checkpoints/        # best.pt / latest.pt (+ *.json sidecars)
├── logs/               # metrics.jsonl, metrics.csv
└── artifacts/          # model artifact metadata, misc
```

`experiment_id` defaults to `<name>-<config_hash[:8]>` (deterministic).

## Trade-offs

- **Custom trainer** costs more code but yields transparency, reproducibility, and a small dependency
  surface — the right trade for a capstone that must explain every step (AC-4 frozen envelope).
- **Train-loss-based checkpointing/early-stopping** keeps M7 free of evaluation; validation-metric-based
  policies become available once M8 provides metrics (via a callback / `metrics_fn`), with no trainer change.

## Consequences

- `app.training` exposes `TrainingConfig`, `Trainer`, `TrainingEngine`, optimizer/scheduler/loss registries,
  `CheckpointManager`, callbacks, `TrainingLogger`, seeding, and `ExperimentRun` — all reusable and
  serializable, torch-guarded.
- The trainer never imports evaluation/API/frontend code; M8 attaches metrics through the callback seam.

## Future improvements

- Validation loop + metric-driven checkpointing/early-stopping (wired in M8 via `metrics_fn`/callback).
- `TensorBoardSink` / MLflow sink behind the existing `MetricSink` abstraction (experiment tracking, M-later).
- Resume-from-checkpoint CLI, EMA weights, LR-range finder, richer AMP, and (if compute grows) DDP.
