"""Controlled-comparison runner (Milestone 11).

Orchestrates one controlled baseline-vs-improved comparison by **reusing** the existing engines — the M7
:class:`Trainer` (no second training engine), the M8 :class:`EvaluationRunner` (no second metrics system),
and M9 :func:`analyze_failures` (no second failure framework). It only *derives* the two arms from a single
:class:`ComparisonConfig` (fairness by construction, then re-checked by the guardrails), records honest
compute measurements, and assembles the canonical :class:`ModelComparisonArtifact`.

Two regimes:

* **synthetic smoke** (``synthetic=True``): trains both arms on small synthetic tensors so the whole
  pipeline is exercised and compute is genuinely MEASURED — but **quality is SYNTHETIC / VALIDATION ONLY**
  and the decision is INCONCLUSIVE.
* **real** (``synthetic=False``): requires a real processed dataset; when absent, quality stays
  **NOT YET MEASURED** and the decision is INCONCLUSIVE (never a fabricated benchmark).

PyTorch is guarded: without it, the runner still produces the infrastructure artifact (guardrails +
INCONCLUSIVE decision) with compute NOT MEASURED.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from app.comparison.config import ComparisonConfig, ExperimentPlan
from app.comparison.decision import (
    REAL_DATA,
    SYNTHETIC_DATA,
    ComparisonDecision,
    DecisionThresholds,
    decide,
)
from app.comparison.failures import compare_failures
from app.comparison.guardrails import FairnessReport, check_fairness
from app.comparison.metrics import compare_metrics
from app.comparison.records import (
    MEASURED,
    NOT_MEASURED,
    NOT_YET_MEASURED,
    SYNTHETIC,
    ComputeComparison,
    ComputeMeasurement,
    ExperimentRecord,
    FailureComparison,
    MetricComparison,
    ModelComparisonArtifact,
)
from app.comparison.viz_specs import comparison_viz_specs
from app.evaluation.records import EvaluationResult
from app.failure_analysis.records import FailureAnalysisResult
from app.models._torch import torch_available
from app.training.seed import capture_environment

logger = logging.getLogger(__name__)


@dataclass
class ArmOutputs:
    """Everything produced for one arm of one seed row."""

    plan: ExperimentPlan
    evaluation_result: EvaluationResult | None
    failure_result: FailureAnalysisResult | None
    compute: ComputeMeasurement
    model_artifact: dict[str, Any] | None
    training_artifact: dict[str, Any] | None
    quality_status: str
    experiment_id: str = ""

    def to_record(self) -> ExperimentRecord:
        from app.evaluation.summary import build_summary
        eval_summary = (build_summary(self.evaluation_result).to_dict()
                        if self.evaluation_result is not None else None)
        failure_summary = None
        if self.failure_result is not None:
            failure_summary = {
                "num_pixel_errors": len(self.failure_result.pixel_errors),
                "num_sample_failures": len(self.failure_result.sample_failures),
            }
        return ExperimentRecord(
            label=self.plan.label, seed=self.plan.seed, architecture=self.plan.model.name,
            experiment_id=self.experiment_id, model_id=self.plan.model_id,
            model_config_hash=self.plan.model.config_hash(),
            training_config_hash=self.plan.training.config_hash(),
            evaluation_config_hash=self.plan.evaluation.config_hash(),
            failure_config_hash=self.plan.failure.config_hash(),
            model_artifact=self.model_artifact, training_artifact=self.training_artifact,
            evaluation_summary=eval_summary, failure_summary=failure_summary,
            compute=self.compute, quality_status=self.quality_status)


@dataclass
class ComparisonResult:
    """The full bundle produced by a comparison run (artifact + typed records + viz specs)."""

    artifact: ModelComparisonArtifact
    fairness: FairnessReport
    metric: MetricComparison
    failure: FailureComparison
    compute: ComputeComparison
    decision: ComparisonDecision
    viz_specs: dict[str, Any] = field(default_factory=dict)
    seeds_executed: list[int] = field(default_factory=list)


def real_data_available(config: ComparisonConfig) -> bool:
    """True only when a real processed dataset for ``config.dataset`` exists locally (never downloads)."""
    from app.core.config import get_settings
    processed = Path(get_settings().data_dir) / "processed" / config.dataset
    return processed.is_dir() and any(processed.iterdir())


class ComparisonRunner:
    """Runs a controlled comparison by reusing the M7/M8/M9 engines (only architecture differs)."""

    def __init__(self, config: ComparisonConfig, *, output_dir: Path | None = None,
                 synthetic: bool = True, synthetic_patch: int = 16, synthetic_batches: int = 2,
                 batch_size: int = 2, thresholds: DecisionThresholds | None = None,
                 data_provider: Any = None) -> None:
        self.config = config
        self.output_dir = Path(output_dir) if output_dir else None
        self.synthetic = synthetic
        self.synthetic_patch = synthetic_patch
        self.synthetic_batches = synthetic_batches
        self.batch_size = batch_size
        self.thresholds = thresholds or DecisionThresholds()
        # Optional REAL-data hook (M12→M11 adapter): a callable ``plan -> (train_loader, test_loader,
        # test_meta)`` supplying real (x,y) tensor batches + per-sample metadata. When set, the comparison
        # runs on REAL data (data_regime=REAL, quality MEASURED) instead of the synthetic generator.
        self.data_provider = data_provider

    # --- public entry point -----------------------------------------------------------------------
    def run(self, seeds: Sequence[int] | None = None) -> ComparisonResult:
        """Execute the comparison for the requested seeds and assemble the artifact."""
        seeds = list(seeds if seeds is not None else self.config.seeds)
        baseline_plan, improved_plan = self.config.plans(seed=seeds[0])

        # Fairness guardrails first — the architecture must be the ONLY intentional difference.
        fairness = check_fairness(baseline_plan, improved_plan, strict=True)
        logger.info("Fairness check passed=%s (compared %d controls).",
                    fairness.passed, len(fairness.compared))

        data_regime = SYNTHETIC_DATA
        quality_status = NOT_YET_MEASURED
        seeds_executed: list[int] = []

        torch_ok = torch_available()
        real_provider = self.data_provider is not None
        can_train = torch_ok and (self.synthetic or real_provider)
        real_ok = real_provider or ((not self.synthetic) and real_data_available(self.config))

        if real_ok:
            data_regime = REAL_DATA
            quality_status = MEASURED
        elif self.synthetic and torch_ok:
            quality_status = SYNTHETIC

        headline: dict[str, ArmOutputs] = {}
        if can_train:
            for seed in seeds:
                b_plan, i_plan = self.config.plans(seed=seed)
                b_out = self._run_arm(b_plan, quality_status)
                i_out = self._run_arm(i_plan, quality_status)
                seeds_executed.append(seed)
                if not headline:                       # headline comparison uses the first seed row
                    headline = {"baseline": b_out, "improved": i_out}
        else:
            # Infrastructure-only (no torch, or real regime with no data): honest empty arms.
            headline = {"baseline": self._empty_arm(baseline_plan, quality_status),
                        "improved": self._empty_arm(improved_plan, quality_status)}

        return self._assemble(headline["baseline"], headline["improved"], fairness,
                              data_regime=data_regime, quality_status=quality_status,
                              seeds=seeds, seeds_executed=seeds_executed, torch_ok=torch_ok)

    # --- per-arm execution ------------------------------------------------------------------------
    def _empty_arm(self, plan: ExperimentPlan, quality_status: str) -> ArmOutputs:
        compute = ComputeMeasurement(
            architecture=plan.model.name, device=plan.training.device,
            batch_size=self.batch_size, measurement_status=NOT_MEASURED,
            notes="torch unavailable or real dataset absent — compute NOT MEASURED.")
        return ArmOutputs(plan=plan, evaluation_result=None, failure_result=None, compute=compute,
                          model_artifact=None, training_artifact=None,
                          quality_status=quality_status, experiment_id=plan.experiment_name)

    def _run_arm(self, plan: ExperimentPlan, quality_status: str) -> ArmOutputs:
        """Train (M7), evaluate (M8), analyse failures (M9), and measure compute for one arm."""
        import numpy as np
        import torch

        from app.evaluation import EvaluationRunner
        from app.failure_analysis import analyze_failures
        from app.models import ModelFactory
        from app.models.summary import count_parameters
        from app.training import Trainer
        from app.training.experiment import create_experiment

        cfg = self.config
        device = plan.training.device
        num_classes = cfg.evaluation.num_classes
        in_ch = plan.model.in_channels
        hw = self.synthetic_patch

        factory = ModelFactory()
        model = factory.create(plan.model)

        # Deterministic synthetic train/test tensors (targets carry a learnable signal from the input).
        def make_loader(seed_offset: int) -> list[tuple[Any, Any]]:
            g = torch.Generator().manual_seed(plan.seed + seed_offset)
            batches = []
            for _ in range(self.synthetic_batches):
                x = torch.rand(self.batch_size, in_ch, hw, hw, generator=g)
                y = x[:, :num_classes].argmax(dim=1).long()      # (B,H,W) in [0, num_classes)
                batches.append((x, y))
            return batches

        test_meta = None
        if self.data_provider is not None:                       # REAL data (M12 adapter)
            train_loader, test_loader, test_meta = self.data_provider(plan)
        else:
            train_loader = make_loader(0)
            test_loader = make_loader(1000)

        # --- train via the reused M7 Trainer (compute MEASURED on synthetic data) ------------------
        arm_dir = None
        run = None
        if self.output_dir is not None:
            run, paths = create_experiment(plan.training, self.output_dir / "experiments")
            arm_dir = paths.root
        trainer = Trainer(plan.training, model, train_loader, output_dir=arm_dir)
        summary = trainer.fit()

        params, trainable = count_parameters(model)
        epochs_run = max(summary.epochs_run, 1)
        avg_epoch = round(summary.duration_seconds / epochs_run, 6)

        # --- inference + evaluation via the reused M8 EvaluationRunner ------------------------------
        model.eval()
        runner = EvaluationRunner(plan.evaluation)
        samples: list[dict[str, Any]] = []
        infer_start = time.time()
        with torch.no_grad():
            for bi, (x, y) in enumerate(test_loader):
                logits = model(x.to(trainer.device))
                preds = logits.argmax(dim=1).cpu().numpy()
                targets = y.numpy()
                runner.update(targets, preds)
                for si in range(targets.shape[0]):
                    if test_meta is not None:
                        m = test_meta[bi][si]
                        sid, grp = m.get("sample_id", f"s{bi}_{si}"), m.get("group", plan.label)
                    else:
                        sid, grp = f"{plan.label}_b{bi}_s{si}", plan.label
                    samples.append({"sample_id": sid, "targets": targets[si],
                                    "predictions": preds[si], "group": grp})
        inference_seconds = round(time.time() - infer_start, 6)
        evaluation_result = runner.compute_result()

        # --- failure analysis via the reused M9 analyzer -------------------------------------------
        failure_result = analyze_failures(plan.failure, confusion=runner.confusion, samples=samples)

        # --- compute measurement (params MEASURED; timings on SYNTHETIC data; memory NOT_MEASURED) --
        peak_memory = NOT_MEASURED
        if trainer.device == "cuda":  # pragma: no cover - no CUDA here
            peak_memory = f"{torch.cuda.max_memory_allocated() / (1024 ** 2):.2f} MiB"
        compute = ComputeMeasurement(
            architecture=plan.model.name, device=trainer.device, batch_size=self.batch_size,
            parameter_count=params, trainable_parameter_count=trainable, epochs_run=epochs_run,
            total_training_seconds=summary.duration_seconds, avg_epoch_seconds=avg_epoch,
            inference_seconds=inference_seconds, peak_memory=peak_memory,
            measurement_status=(MEASURED if quality_status == MEASURED else SYNTHETIC),
            notes=("Parameters MEASURED; timings MEASURED on real data; peak memory NOT MEASURED on "
                   "cpu/mps." if quality_status == MEASURED else
                   "Parameters MEASURED; timings measured on SYNTHETIC data (VALIDATION ONLY); "
                   "peak memory NOT MEASURED on cpu/mps."))

        # --- artifacts (reuse M6/M7) ----------------------------------------------------------------
        model_artifact = factory.build_artifact(plan.model, dataset_version=cfg.dataset_version).to_dict()
        training_artifact = None
        experiment_id = plan.experiment_name
        if run is not None:
            training_artifact = trainer.build_training_artifact(run, model_artifact=None).to_dict()
            experiment_id = run.experiment_id
        else:
            training_artifact = trainer.build_training_artifact(
                {"experiment_id": plan.experiment_name}, model_artifact=None).to_dict()

        return ArmOutputs(
            plan=plan, evaluation_result=evaluation_result, failure_result=failure_result,
            compute=compute, model_artifact=model_artifact, training_artifact=training_artifact,
            quality_status=quality_status, experiment_id=experiment_id)

    # --- assembly ---------------------------------------------------------------------------------
    def _assemble(self, baseline: ArmOutputs, improved: ArmOutputs, fairness: FairnessReport, *,
                  data_regime: str, quality_status: str, seeds: list[int], seeds_executed: list[int],
                  torch_ok: bool) -> ComparisonResult:
        # Quality / failure comparison only when both arms produced results.
        if baseline.evaluation_result is not None and improved.evaluation_result is not None:
            metric = compare_metrics(baseline.evaluation_result, improved.evaluation_result,
                                     status=quality_status)
        else:
            metric = MetricComparison(status=quality_status)

        if baseline.failure_result is not None and improved.failure_result is not None:
            failure = compare_failures(baseline.failure_result, improved.failure_result,
                                       top_k=self.config.top_k, status=quality_status)
        else:
            failure = FailureComparison(status=quality_status)

        compute = ComputeComparison.of(baseline.compute, improved.compute)
        decision = decide(metric, failure, compute, data_regime=data_regime,
                          seeds_executed=len(seeds_executed), thresholds=self.thresholds)

        limitations = self._limitations(data_regime, quality_status, seeds_executed, torch_ok)
        artifact = ModelComparisonArtifact.create(
            comparison_config_hash=self.config.config_hash(), fairness_hash=self.config.fairness_hash(),
            baseline=baseline.to_record(), improved=improved.to_record(),
            fairness_report=fairness.to_dict(), metric_comparison=metric.to_dict(),
            failure_comparison=failure.to_dict(), compute_comparison=compute.to_dict(),
            decision=decision.to_dict(), environment=capture_environment().to_dict(),
            seeds_intended=list(seeds), seeds_executed=list(seeds_executed),
            limitations=limitations, data_regime=data_regime,
            notes=f"Controlled comparison '{self.config.comparison_name}'.")

        viz = comparison_viz_specs(metric, failure, compute)
        return ComparisonResult(artifact=artifact, fairness=fairness, metric=metric, failure=failure,
                                compute=compute, decision=decision, viz_specs=viz,
                                seeds_executed=list(seeds_executed))

    def _limitations(self, data_regime: str, quality_status: str, seeds_executed: list[int],
                     torch_ok: bool) -> list[str]:
        lines: list[str] = []
        if data_regime != REAL_DATA:
            lines.append("Real-data quality: NOT YET MEASURED (no real processed dataset present).")
        if quality_status == SYNTHETIC:
            lines.append("Reported metrics are SYNTHETIC / VALIDATION ONLY — not a benchmark, not "
                         "real-data performance.")
        if not torch_ok:
            lines.append("PyTorch unavailable — training/evaluation/compute NOT MEASURED "
                         "(infrastructure only).")
        n = len(seeds_executed)
        if n < self.thresholds.min_seeds_for_significance:
            lines.append(f"Statistical significance NOT MEASURED — only {n} seed row(s) executed "
                         f"(intended matrix: seeds {list(self.config.seeds)}).")
        lines.append("Peak memory / FLOPs: NOT MEASURED on cpu/mps (never inferred from parameter count).")
        lines.append("Decision is INCONCLUSIVE until real controlled training + evaluation is executed.")
        return lines


def run_synthetic_comparison(config: ComparisonConfig, *, output_dir: Path | None = None,
                             seeds: Sequence[int] | None = None, synthetic_patch: int = 16,
                             batch_size: int = 2, synthetic_batches: int = 2) -> ComparisonResult:
    """Convenience: run a synthetic smoke comparison (VALIDATION ONLY) for the given config."""
    runner = ComparisonRunner(config, output_dir=output_dir, synthetic=True,
                              synthetic_patch=synthetic_patch, batch_size=batch_size,
                              synthetic_batches=synthetic_batches)
    return runner.run(seeds=seeds)
