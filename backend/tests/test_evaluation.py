"""Milestone 8 verification: evaluation framework (synthetic data only, no real dataset).

Covers perfect/wrong/partial predictions, absent classes, ignored pixels, empty masks, binary + multiclass
evaluation, per-class/macro/micro/weighted aggregation, confusion matrix, deterministic accumulation,
batch-vs-global aggregation equality, serialization, stratification, and undefined-metric handling.
Metric math is pure-stdlib; array-accumulation tests require numpy (skipped otherwise).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import ConfigurationError, EvaluationError
from app.evaluation.aggregation import compute_aggregates, macro_average
from app.evaluation.config import EvaluationConfig, EvaluationMode
from app.evaluation.confusion import ConfusionMatrix
from app.evaluation.metrics import compute_class_metrics, pixel_accuracy
from app.evaluation.records import EvaluationRun, EvaluationResult, MetricValue
from app.evaluation.runner import EvaluationRunner, build_result
from app.evaluation.summary import build_summary

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


def _cm_from(matrix: list[list[int]], names: list[str], ignore=None) -> ConfusionMatrix:
    return ConfusionMatrix(num_classes=len(matrix), matrix=matrix, class_names=names, ignore_index=ignore)


# ---------------------------------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------------------------------

def test_config_validation_and_hash() -> None:
    with pytest.raises(ConfigurationError):
        EvaluationConfig(num_classes=3, class_names=("a", "b"))   # mismatch
    with pytest.raises(ConfigurationError):
        EvaluationConfig(mode="binary", num_classes=4, class_names=("a", "b", "c", "d"))
    a = EvaluationConfig.cloudsen12(split="test")
    assert a.config_hash() == EvaluationConfig.cloudsen12(split="test").config_hash()
    assert a.mode == EvaluationMode.MULTICLASS.value and a.num_classes == 4
    b = EvaluationConfig.on_cloud_n(split="test")
    assert b.num_classes == 2 and b.class_names == ("no_cloud", "cloud")


# ---------------------------------------------------------------------------------------------------
# Metrics from a known confusion matrix (no numpy needed)
# ---------------------------------------------------------------------------------------------------

def test_perfect_predictions() -> None:
    cm = _cm_from([[5, 0], [0, 3]], ["non_cloud", "cloud"])
    per_class = compute_class_metrics(cm)
    for c in per_class:
        assert c.metrics["iou"].value == 1.0 and c.metrics["f1"].value == 1.0
    assert pixel_accuracy(cm).value == 1.0


def test_completely_wrong_predictions() -> None:
    cm = _cm_from([[0, 4], [3, 0]], ["non_cloud", "cloud"])   # everything misclassified
    per_class = compute_class_metrics(cm)
    for c in per_class:
        assert c.metrics["iou"].value == 0.0        # tp=0 but fp/fn>0 -> defined 0.0
    assert pixel_accuracy(cm).value == 0.0


def test_partially_correct_and_precision_recall() -> None:
    # class 1 (cloud): tp=3, fp=1, fn=2
    cm = _cm_from([[4, 1], [2, 3]], ["non_cloud", "cloud"])
    cloud = compute_class_metrics(cm)[1]
    assert cloud.tp == 3 and cloud.fp == 1 and cloud.fn == 2
    assert abs(cloud.metrics["precision"].value - 0.75) < 1e-9
    assert abs(cloud.metrics["recall"].value - 0.6) < 1e-9
    assert abs(cloud.metrics["iou"].value - 3 / 6) < 1e-9


def test_absent_class_metrics_are_undefined() -> None:
    # class 1 absent in both prediction and ground truth -> all-undefined for class 1
    cm = _cm_from([[7, 0], [0, 0]], ["clear", "cloud"])
    cloud = compute_class_metrics(cm)[1]
    assert cloud.metrics["iou"].defined is False and cloud.metrics["iou"].value is None
    assert cloud.metrics["recall"].defined is False
    assert "absent" in cloud.metrics["recall"].reason


def test_empty_mask_pixel_accuracy_undefined() -> None:
    cm = _cm_from([[0, 0], [0, 0]], ["a", "b"])
    assert pixel_accuracy(cm).defined is False


# ---------------------------------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------------------------------

def test_macro_excludes_undefined_classes() -> None:
    cm = _cm_from([[7, 0], [0, 0]], ["clear", "cloud"])   # cloud undefined
    per_class = compute_class_metrics(cm)
    macro_iou = macro_average(per_class, "iou")
    assert macro_iou.defined and macro_iou.value == 1.0          # only 'clear' counted
    assert "1/2 classes included" in macro_iou.reason


def test_macro_micro_weighted_present() -> None:
    cm = _cm_from([[4, 1], [2, 3]], ["a", "b"])
    aggs = compute_aggregates(compute_class_metrics(cm), cm)
    for group in ("macro", "micro", "weighted"):
        assert set(aggs[group]) == {"iou", "dice", "precision", "recall", "f1"}
    # micro f1 == pixel accuracy for single-label
    assert abs(aggs["micro"]["f1"].value - pixel_accuracy(cm).value) < 1e-9


# ---------------------------------------------------------------------------------------------------
# Confusion matrix semantics
# ---------------------------------------------------------------------------------------------------

def test_confusion_counts_and_add() -> None:
    cm = _cm_from([[4, 1], [2, 3]], ["a", "b"])
    assert cm.tp(1) == 3 and cm.fp(1) == 1 and cm.fn(1) == 2 and cm.support(1) == 5
    assert cm.tn(0) == 3  # total 10 - tp0(4) - fp0(2) - fn0(1)
    summed = cm.add(cm)
    assert summed.matrix == [[8, 2], [4, 6]]
    # serialization roundtrip
    assert ConfusionMatrix.from_dict(cm.to_dict()).matrix == cm.matrix


# ---------------------------------------------------------------------------------------------------
# numpy accumulation / runner (requires numpy)
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_multiclass_runner_and_deterministic() -> None:
    cfg = EvaluationConfig.cloudsen12(split="test")
    t = np.array([[0, 1], [2, 3]])
    r1 = EvaluationRunner(cfg).run([(t, t.copy())])
    r2 = EvaluationRunner(cfg).run([(t, t.copy())])
    assert r1.to_dict() == r2.to_dict()                         # deterministic
    assert all(c.metrics["iou"].value == 1.0 for c in r1.per_class)


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_batch_vs_global_aggregation_equal() -> None:
    cfg = EvaluationConfig.cloudsen12(split="test")
    b1 = (np.array([0, 0, 1, 1]), np.array([0, 1, 1, 1]))
    b2 = (np.array([2, 2, 3, 3]), np.array([2, 2, 3, 0]))
    batched = EvaluationRunner(cfg)
    batched.update(*b1); batched.update(*b2)
    r_batched = batched.compute_result()
    allt = np.concatenate([b1[0], b2[0]]); allp = np.concatenate([b1[1], b2[1]])
    r_global = EvaluationRunner(cfg).run([(allt, allp)])
    # metric(accumulate(b1)+accumulate(b2)) == metric(accumulate(all))
    assert r_batched.confusion.matrix == r_global.confusion.matrix
    assert r_batched.to_dict() == r_global.to_dict()


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_ignored_pixels_excluded() -> None:
    cfg = EvaluationConfig.cloudsen12(split="test", ignore_index=255)
    t = np.array([0, 1, 255, 2])   # one ignored pixel
    p = np.array([0, 1, 0, 2])     # prediction at ignored pixel must not count
    result = EvaluationRunner(cfg).run([(t, p)])
    assert result.confusion.total() == 3   # ignored pixel excluded


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_out_of_range_labels_raise() -> None:
    cfg = EvaluationConfig.on_cloud_n(split="test")
    with pytest.raises(EvaluationError):
        EvaluationRunner(cfg).run([(np.array([0, 5]), np.array([0, 1]))])   # label 5 out of range


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_argmax_logits_path() -> None:
    cfg = EvaluationConfig.on_cloud_n(split="test")
    targets = np.array([[0, 1], [1, 0]])
    logits = np.zeros((2, 2, 2))          # (C=2, H=2, W=2); argmax -> all class 0
    logits[1] = 1.0                       # class 1 wins everywhere
    result = EvaluationRunner(cfg).run([(targets, logits)], is_logits=True)
    assert result.confusion.predicted(1) == 4   # all predicted cloud


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_binary_collapse_opt_in() -> None:
    from app.evaluation.binary import collapse_to_binary
    labels = np.array([0, 1, 2, 3])   # clear, thick, thin, shadow
    binary = collapse_to_binary(labels)
    assert list(binary) == [0, 1, 1, 0]   # thick+thin -> cloud


# ---------------------------------------------------------------------------------------------------
# Stratified evaluation + serialization
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_stratified_evaluation_and_class_view() -> None:
    from app.evaluation.stratification import stratified_evaluation
    cfg = EvaluationConfig.cloudsen12(split="test")
    t = np.array([0, 1, 2, 3])
    batches = [(t, t.copy(), "region_a"), (t, np.array([0, 0, 2, 3]), "region_b")]
    strat = stratified_evaluation(cfg, batches)
    assert set(strat.by_group) == {"region_a", "region_b"}
    # thin_cloud is always visible in the per-class view
    assert "thin_cloud" in strat.by_class
    assert strat.by_class["thin_cloud"].metrics["iou"].defined


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_run_serialization_roundtrip_and_summary(tmp_path: Path) -> None:
    cfg = EvaluationConfig.cloudsen12(split="test", model_id="m1")
    t = np.array([0, 1, 2, 3]); p = np.array([0, 1, 2, 0])
    runner = EvaluationRunner(cfg)
    result = runner.run([(t, p)])
    run = runner.build_run(result)
    # JSON roundtrip preserves the confusion matrix + metrics
    restored = EvaluationRun.from_json(run.to_json())
    assert restored.result.confusion.matrix == run.result.confusion.matrix
    path = run.save_json(tmp_path / "run.json")
    assert EvaluationRun.load_json(path).config_hash == run.config_hash
    # summary surfaces thin cloud + worst class
    summary = build_summary(result)
    assert "thin_cloud" in summary.per_class_iou
    assert summary.thin_cloud_iou is not None
    assert summary.worst_class_by_iou is not None
