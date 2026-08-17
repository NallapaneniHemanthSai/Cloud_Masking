"""Milestone 11 verification: controlled model comparison (synthetic data only).

Runs under pytest **and** standalone (``python backend/tests/test_comparison.py``) so it doubles as the
manual harness when pytest is unavailable — it imports no third-party test framework. numpy/torch are
guarded: tests needing them are skipped (reported) when absent.

Covers: config validation, deterministic config hash, fairness guardrails + mismatch detection, model
pairing, metric comparison, thin-cloud extraction, compute comparison, the decision framework (all five
outcomes incl. INCONCLUSIVE), artifact serialization + deterministic hash, the synthetic end-to-end run,
and M5/M8/M9 integration + baseline/Attention-U-Net regressions.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.comparison import (  # noqa: E402
    ClassMetricDelta,
    ComparisonConfig,
    ComputeComparison,
    ComputeMeasurement,
    DecisionOutcome,
    DecisionThresholds,
    ExperimentRecord,
    FailureComparison,
    MetricComparison,
    ModelComparisonArtifact,
    ThinCloudComparison,
    check_config_fairness,
    check_fairness,
    comparison_viz_specs,
    compare_failures,
    compare_metrics,
    decide,
    extract_thin_cloud,
    run_synthetic_comparison,
)
from app.comparison.decision import REAL_DATA, SYNTHETIC_DATA  # noqa: E402
from app.comparison.records import MEASURED, NOT_YET_MEASURED, SYNTHETIC  # noqa: E402
from app.core.exceptions import ConfigurationError, GuardrailViolation  # noqa: E402
from app.evaluation.config import CLOUDSEN12_CLASS_NAMES, EvaluationConfig  # noqa: E402
from app.evaluation.confusion import ConfusionMatrix  # noqa: E402
from app.evaluation.runner import build_result  # noqa: E402
from app.failure_analysis import FailureAnalysisConfig, analyze_failures  # noqa: E402
from app.models._torch import torch_available  # noqa: E402
from app.models.config import ModelConfig  # noqa: E402
from app.visualization.records import FigureKind  # noqa: E402

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


@contextmanager
def assert_raises(exc_type):
    """Dependency-free replacement for ``pytest.raises`` (keeps the harness framework-free)."""
    try:
        yield
    except exc_type:
        return
    except Exception as other:  # noqa: BLE001
        raise AssertionError(f"expected {exc_type.__name__}, got {type(other).__name__}: {other}")
    raise AssertionError(f"expected {exc_type.__name__}, but no exception was raised")


def _small_config(seed: int = 1) -> ComparisonConfig:
    return ComparisonConfig.cloudsen12(patch_size=16, encoder_depth=2, base_channels=8, epochs=1,
                                       batch_size=2, device="cpu", seed=seed)


def _result(matrix: list[list[int]]):
    cm = ConfusionMatrix(4, matrix, list(CLOUDSEN12_CLASS_NAMES))
    return build_result(cm, EvaluationConfig.cloudsen12(split="test"))


# --------------------------------------------------------------------------------------------------
# 1. Config validation + deterministic config hash
# --------------------------------------------------------------------------------------------------
def test_config_validation_rejects_identical_models() -> None:
    with assert_raises(ConfigurationError):
        ComparisonConfig(baseline_model=ModelConfig(name="unet"),
                         improved_model=ModelConfig(name="unet"))


def test_config_validation_rejects_class_mismatch() -> None:
    with assert_raises(ConfigurationError):
        ComparisonConfig(baseline_model=ModelConfig(name="unet", num_classes=3),
                         improved_model=ModelConfig(name="attention_unet", num_classes=3),
                         evaluation=EvaluationConfig.cloudsen12(split="test"))  # eval has 4 classes


def test_config_hash_is_deterministic_and_roundtrips() -> None:
    cfg = _small_config()
    assert cfg.config_hash() == _small_config().config_hash()
    assert cfg.config_hash() == ComparisonConfig.from_dict(cfg.to_dict()).config_hash()
    # Changing the improved architecture changes the config hash but NOT the fairness hash.
    other = ComparisonConfig.cloudsen12(improved="unet", baseline="attention_unet", patch_size=16,
                                        encoder_depth=2, base_channels=8, epochs=1, device="cpu", seed=1)
    assert other.config_hash() != cfg.config_hash()


def test_fairness_hash_ignores_architecture() -> None:
    # Same shared controls but the two arms swapped -> identical fairness hash, different config hash.
    a = _small_config()  # baseline=unet, improved=attention_unet
    b = ComparisonConfig.cloudsen12(baseline="attention_unet", improved="unet", patch_size=16,
                                    encoder_depth=2, base_channels=8, epochs=1, batch_size=2,
                                    device="cpu", seed=1)
    assert a.fairness_hash() == b.fairness_hash()   # architecture pairing does not affect fairness hash
    assert a.config_hash() != b.config_hash()       # but the whole-comparison hash does differ


# --------------------------------------------------------------------------------------------------
# 2. Fairness guardrails + mismatch detection + model pairing
# --------------------------------------------------------------------------------------------------
def test_fairness_passes_for_derived_plans_and_reports_all_fields() -> None:
    report = check_config_fairness(_small_config(), strict=True)
    assert report.passed is True
    assert not report.mismatches
    assert len(report.compared) >= 20            # reports ALL compared controls
    assert "training.optimizer" in report.compared_fields
    assert "training.loss" in report.compared_fields
    assert "evaluation.split" in report.compared_fields


def test_fairness_detects_mismatch_and_raises() -> None:
    import dataclasses

    from app.training.config import TrainingConfig
    cfg = _small_config()
    baseline, improved = cfg.plans(seed=1)
    tampered = TrainingConfig.from_dict({**improved.training.to_dict(),
                                         "optimizer": {"name": "sgd", "lr": 0.5, "weight_decay": 0.0,
                                                       "momentum": 0.9, "params": {}}})
    improved_bad = dataclasses.replace(improved, training=tampered)
    with assert_raises(GuardrailViolation):
        check_fairness(baseline, improved_bad, strict=True)
    report = check_fairness(baseline, improved_bad, strict=False)
    assert report.passed is False
    assert "training.optimizer" in [m.field for m in report.mismatches]


def test_fairness_rejects_same_architecture_pairing() -> None:
    import dataclasses
    cfg = _small_config()
    baseline, improved = cfg.plans(seed=1)
    same = dataclasses.replace(improved, model=baseline.model)
    with assert_raises(GuardrailViolation):
        check_fairness(baseline, same, strict=True)


def test_model_pairing() -> None:
    baseline, improved = _small_config().plans(seed=7)
    assert baseline.label == "baseline" and baseline.model.name == "unet"
    assert improved.label == "improved" and improved.model.name == "attention_unet"
    assert baseline.seed == 7 and improved.seed == 7
    assert baseline.training.seed == 7 and improved.training.seed == 7


# --------------------------------------------------------------------------------------------------
# 3. Metric comparison + thin-cloud extraction (reuses M8)
# --------------------------------------------------------------------------------------------------
_BASE_MATRIX = [[10, 0, 0, 0], [0, 10, 0, 0], [0, 0, 8, 2], [0, 0, 0, 10]]   # thin IoU = 8/10 = 0.8
_IMPR_MATRIX = [[10, 0, 0, 0], [0, 10, 0, 0], [0, 0, 10, 0], [0, 0, 0, 10]]  # thin IoU = 1.0
_REG_MATRIX = [[10, 0, 0, 0], [0, 10, 0, 0], [0, 0, 5, 5], [0, 0, 0, 10]]    # thin IoU = 0.5


def test_metric_comparison_computes_deltas() -> None:
    mc = compare_metrics(_result(_BASE_MATRIX), _result(_IMPR_MATRIX), status=MEASURED)
    thin = next(c for c in mc.per_class if c.class_name == "thin_cloud")
    assert abs(thin.baseline["iou"] - 0.8) < 1e-6
    assert abs(thin.improved["iou"] - 1.0) < 1e-6
    assert abs(thin.delta["iou"] - 0.2) < 1e-6
    assert mc.macro_delta["iou"] is not None and mc.macro_delta["iou"] > 0


def test_thin_cloud_extraction() -> None:
    tc = extract_thin_cloud(_result(_BASE_MATRIX), _result(_IMPR_MATRIX), status=MEASURED)
    assert abs(tc.iou_delta - 0.2) < 1e-6
    assert tc.regressed is False
    assert tc.baseline_false_negatives == 2 and tc.improved_false_negatives == 0
    assert tc.false_negative_delta == -2

    tc_reg = extract_thin_cloud(_result(_BASE_MATRIX), _result(_REG_MATRIX), status=MEASURED)
    assert tc_reg.regressed is True and tc_reg.iou_delta < 0


# --------------------------------------------------------------------------------------------------
# 4. Compute comparison
# --------------------------------------------------------------------------------------------------
def test_compute_comparison_ratios() -> None:
    b = ComputeMeasurement(architecture="unet", device="cpu", batch_size=2, parameter_count=1000,
                           total_training_seconds=2.0, inference_seconds=1.0, measurement_status=SYNTHETIC)
    i = ComputeMeasurement(architecture="attention_unet", device="cpu", batch_size=2,
                           parameter_count=2000, total_training_seconds=3.0, inference_seconds=2.0,
                           measurement_status=SYNTHETIC)
    cc = ComputeComparison.of(b, i)
    assert cc.parameter_ratio == 2.0 and cc.parameter_delta == 1000
    assert cc.training_time_ratio == 1.5 and cc.inference_time_ratio == 2.0
    assert cc.status == SYNTHETIC


# --------------------------------------------------------------------------------------------------
# 5. Decision framework — all five outcomes
# --------------------------------------------------------------------------------------------------
def _metric(thin_iou_delta, macro_iou_delta, *, regressed=False, worst="thin_cloud",
            status=MEASURED) -> MetricComparison:
    thin = ThinCloudComparison(baseline_iou=0.8, improved_iou=0.8 + (thin_iou_delta or 0),
                               iou_delta=thin_iou_delta, dice_delta=thin_iou_delta, regressed=regressed,
                               status=status)
    per_class = [ClassMetricDelta("thin_cloud", {"iou": 0.8}, {"iou": 0.8 + (thin_iou_delta or 0)},
                                  {"iou": thin_iou_delta})]
    return MetricComparison(macro_delta={"iou": macro_iou_delta}, thin_cloud=thin,
                            per_class=per_class, worst_class_baseline=worst, status=status)


def _compute(param_ratio=1.0) -> ComputeComparison:
    b = ComputeMeasurement("unet", "cpu", 2, parameter_count=1000, total_training_seconds=1.0,
                           measurement_status=MEASURED)
    i = ComputeMeasurement("attention_unet", "cpu", 2, parameter_count=int(1000 * param_ratio),
                           total_training_seconds=param_ratio, measurement_status=MEASURED)
    return ComputeComparison.of(b, i)


def test_decision_inconclusive_on_synthetic() -> None:
    d = decide(_metric(0.2, 0.05, status=SYNTHETIC), FailureComparison(status=SYNTHETIC),
               _compute(), data_regime=SYNTHETIC_DATA, seeds_executed=3)
    assert d.outcome == DecisionOutcome.INCONCLUSIVE.value


def test_decision_improved() -> None:
    d = decide(_metric(0.2, 0.05), FailureComparison(status=MEASURED), _compute(1.05),
               data_regime=REAL_DATA, seeds_executed=3)
    assert d.outcome == DecisionOutcome.IMPROVED.value


def test_decision_regression_when_thin_cloud_drops_even_if_aggregate_up() -> None:
    d = decide(_metric(-0.1, 0.05, regressed=True), FailureComparison(status=MEASURED), _compute(1.05),
               data_regime=REAL_DATA, seeds_executed=3)
    assert d.outcome == DecisionOutcome.REGRESSION.value


def test_decision_compute_unjustified() -> None:
    # Slight thin-cloud gain (0.02 < small_gain 0.03) but 2x params -> trade-off not justified.
    d = decide(_metric(0.02, 0.02), FailureComparison(status=MEASURED), _compute(2.0),
               data_regime=REAL_DATA, seeds_executed=3, thresholds=DecisionThresholds())
    assert d.outcome == DecisionOutcome.COMPUTE_UNJUSTIFIED.value


def test_decision_no_significant_improvement() -> None:
    d = decide(_metric(0.0, 0.0), FailureComparison(status=MEASURED), _compute(1.0),
               data_regime=REAL_DATA, seeds_executed=3)
    assert d.outcome == DecisionOutcome.NO_SIGNIFICANT_IMPROVEMENT.value


def test_decision_single_seed_flags_uncertainty() -> None:
    d = decide(_metric(0.2, 0.05), FailureComparison(status=MEASURED), _compute(1.05),
               data_regime=REAL_DATA, seeds_executed=1)
    assert d.uncertainty_status == "NOT_MEASURED"
    assert any("significance NOT MEASURED" in r for r in d.rationale)


# --------------------------------------------------------------------------------------------------
# 6. Artifact serialization + deterministic hash
# --------------------------------------------------------------------------------------------------
def _artifact() -> ModelComparisonArtifact:
    base = ExperimentRecord(label="baseline", seed=1, architecture="unet", experiment_id="e-b",
                            model_id="unet-1", model_config_hash="ha", training_config_hash="ta")
    impr = ExperimentRecord(label="improved", seed=1, architecture="attention_unet",
                            experiment_id="e-i", model_id="aunet-1", model_config_hash="hb",
                            training_config_hash="tb")
    return ModelComparisonArtifact.create(comparison_config_hash="cfg", fairness_hash="fair",
                                          baseline=base, improved=impr,
                                          decision={"outcome": "INCONCLUSIVE"})


def test_artifact_roundtrip() -> None:
    a = _artifact()
    b = ModelComparisonArtifact.from_dict(a.to_dict())
    assert b.comparison_id == a.comparison_id
    assert b.content_hash() == a.content_hash()
    assert b.baseline.architecture == "unet" and b.improved.architecture == "attention_unet"


def test_artifact_hash_ignores_timestamps_and_notes() -> None:
    import dataclasses
    a = _artifact()
    b = dataclasses.replace(a, created_at="2000-01-01T00:00:00+00:00", notes="totally different note")
    assert a.content_hash() == b.content_hash()
    assert a.comparison_id == f"cmp-{a.content_hash()[:12]}"


# --------------------------------------------------------------------------------------------------
# 7. M5 / M8 / M9 integration + synthetic end-to-end
# --------------------------------------------------------------------------------------------------
def test_m5_viz_specs_integration() -> None:
    mc = compare_metrics(_result(_BASE_MATRIX), _result(_IMPR_MATRIX), status=MEASURED)
    specs = comparison_viz_specs(mc, FailureComparison(status=MEASURED), _compute())
    assert set(specs) == {"metric_comparison", "per_class_comparison", "thin_cloud_comparison",
                          "compute_vs_quality", "failure_category_comparison"}
    for spec in specs.values():
        assert spec["kind"] == FigureKind.BAR.value
        assert "series" in spec["payload"]


def test_m9_failure_comparison_integration() -> None:
    if not HAS_NUMPY:
        print("SKIP test_m9_failure_comparison_integration (numpy unavailable)")
        return
    cfg = FailureAnalysisConfig(dataset="cloudsen12", split="test", mode="multiclass",
                                class_names=CLOUDSEN12_CLASS_NAMES, model_id="m", top_k=3)
    cm_b = ConfusionMatrix(4, _BASE_MATRIX, list(CLOUDSEN12_CLASS_NAMES))
    cm_i = ConfusionMatrix(4, _IMPR_MATRIX, list(CLOUDSEN12_CLASS_NAMES))
    fb = analyze_failures(cfg, confusion=cm_b)
    fi = analyze_failures(cfg, confusion=cm_i)
    fc = compare_failures(fb, fi, status=MEASURED)
    # Improved matrix has no thin-cloud FN; baseline has 2.
    assert fc.baseline.thin_cloud_failures == 2 and fc.improved.thin_cloud_failures == 0
    assert fc.thin_cloud_failure_delta == -2
    assert fc.hypothesis_supported is True   # MEASURED + fewer thin failures + fewer FN


def test_synthetic_end_to_end() -> None:
    if not torch_available():
        print("SKIP test_synthetic_end_to_end (torch unavailable)")
        return
    result = run_synthetic_comparison(_small_config(), seeds=[1, 2], synthetic_patch=16)
    a = result.artifact
    assert a.data_regime == SYNTHETIC_DATA
    assert result.decision.outcome == DecisionOutcome.INCONCLUSIVE.value
    assert result.metric.status == SYNTHETIC
    assert result.compute.baseline.parameter_count == 30372     # baseline U-Net regression pin
    assert result.compute.improved.parameter_count == 30782     # Attention U-Net regression pin
    assert result.compute.improved.parameter_count > result.compute.baseline.parameter_count
    assert result.seeds_executed == [1, 2]
    # Deterministic artifact hash across a serialization round-trip.
    assert ModelComparisonArtifact.from_dict(a.to_dict()).content_hash() == a.content_hash()


# --------------------------------------------------------------------------------------------------
# 8. Baseline / Attention-U-Net regressions (architecture unchanged)
# --------------------------------------------------------------------------------------------------
def test_baseline_and_attention_regression() -> None:
    if not torch_available():
        print("SKIP test_baseline_and_attention_regression (torch unavailable)")
        return
    from app.models import ModelFactory
    from app.models.summary import count_parameters
    unet = ModelConfig(name="unet", in_channels=13, num_classes=4, encoder_depth=2, base_channels=8)
    attn = ModelConfig(name="attention_unet", in_channels=13, num_classes=4, encoder_depth=2,
                       base_channels=8)
    u_tot, _ = count_parameters(ModelFactory().create(unet))
    a_tot, _ = count_parameters(ModelFactory().create(attn))
    assert u_tot == 30372, f"baseline U-Net params changed: {u_tot}"
    assert a_tot == 30782, f"Attention U-Net params changed: {a_tot}"
    assert a_tot > u_tot        # attention gates add parameters
    # Config hashes are stable identifiers.
    assert unet.config_hash() == ModelConfig.from_dict(unet.to_dict()).config_hash()


# --------------------------------------------------------------------------------------------------
# Manual harness (used when pytest is unavailable).
# --------------------------------------------------------------------------------------------------
def _run_all() -> int:
    tests = [(name, obj) for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
