"""Milestone 9 verification: failure / confusing-case analysis (synthetic data only).

Metric/record logic is pure-stdlib; array-based sample analysis requires numpy (skipped otherwise).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import ConfigurationError, FailureAnalysisError
from app.evaluation.config import CLOUDSEN12_CLASS_NAMES
from app.evaluation.confusion import ConfusionMatrix
from app.failure_analysis.analyzer import analyze_failures
from app.failure_analysis.config import FailureAnalysisConfig, SeverityThresholds
from app.failure_analysis.pixel_analysis import analyze_pixels
from app.failure_analysis.ranking import dedup_by_sample, rank_samples, top_k
from app.failure_analysis.records import FailureAnalysisResult, SampleFailure
from app.failure_analysis.taxonomy import (
    CATEGORY_MEASURABILITY,
    FailureCategory,
    Measurability,
    Severity,
)
from app.failure_analysis.viz_specs import confusing_case_specs

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False

CFG = FailureAnalysisConfig(dataset="cloudsen12", split="test", mode="multiclass",
                            class_names=CLOUDSEN12_CLASS_NAMES, model_id="m1", top_k=3)


def _cm(matrix, names=CLOUDSEN12_CLASS_NAMES):
    return ConfusionMatrix(len(matrix), matrix, list(names))


def _sf(sid, rate, count=None, severity="LOW", categories=None, per_class=None, group="A"):
    return SampleFailure(sample_id=sid, dataset="cloudsen12", split="test", total_pixels=100,
                         error_count=count if count is not None else int(rate * 100), error_rate=rate,
                         per_class_errors=per_class or {}, categories=categories or [],
                         severity=severity, group=group)


# ---------------------------------------------------------------------------------------------------
# Taxonomy + config + severity
# ---------------------------------------------------------------------------------------------------

def test_taxonomy_measurability_marks_deferred_and_not_measurable() -> None:
    assert CATEGORY_MEASURABILITY[FailureCategory.THIN_CLOUD_FAILURE] == Measurability.MEASURABLE
    assert CATEGORY_MEASURABILITY[FailureCategory.EDGE_ERROR] == Measurability.DEFERRED
    assert CATEGORY_MEASURABILITY[FailureCategory.HIGH_CONFIDENCE_ERROR] == Measurability.NOT_MEASURABLE


def test_config_validation_and_hash() -> None:
    with pytest.raises(ConfigurationError):
        FailureAnalysisConfig(top_k=0)
    with pytest.raises(ConfigurationError):
        FailureAnalysisConfig(severity_thresholds=SeverityThresholds(critical=0.2, high=0.5, medium=0.3))
    assert CFG.config_hash() == FailureAnalysisConfig(
        dataset="cloudsen12", split="test", mode="multiclass",
        class_names=CLOUDSEN12_CLASS_NAMES, model_id="m1", top_k=3).config_hash()


def test_severity_thresholds() -> None:
    st = SeverityThresholds()
    assert st.severity_for(0.0) == Severity.NONE
    assert st.severity_for(0.1) == Severity.LOW
    assert st.severity_for(0.3) == Severity.MEDIUM
    assert st.severity_for(0.6) == Severity.HIGH
    assert st.severity_for(0.9) == Severity.CRITICAL


# ---------------------------------------------------------------------------------------------------
# Pixel-level analysis (reuses confusion; no numpy)
# ---------------------------------------------------------------------------------------------------

def test_perfect_predictions_have_zero_errors() -> None:
    cm = _cm([[3, 0, 0, 0], [0, 3, 0, 0], [0, 0, 3, 0], [0, 0, 0, 3]])
    errors = analyze_pixels(cm, CFG)
    assert sum(e.error_count for e in errors) == 0


def test_false_negative_and_confusion_detected() -> None:
    # true thin_cloud(2) mispredicted as clear(0): 2 pixels
    cm = _cm([[5, 0, 0, 0], [0, 5, 0, 0], [2, 0, 3, 0], [0, 0, 0, 5]])
    errors = analyze_pixels(cm, CFG)
    fn = next(e for e in errors if e.class_name == "thin_cloud" and e.error_type == "false_negative")
    assert fn.error_count == 2 and fn.predicted_class == "clear"
    conf = next(e for e in errors if e.class_name == "thin_cloud" and e.error_type == "class_confusion")
    assert conf.predicted_class == "clear" and conf.error_count == 2


def test_false_positive_detected() -> None:
    # clear predicted where truth was thin cloud -> clear has FP
    cm = _cm([[5, 0, 0, 0], [0, 5, 0, 0], [2, 0, 3, 0], [0, 0, 0, 5]])
    fp = next(e for e in analyze_pixels(cm, CFG)
              if e.class_name == "clear" and e.error_type == "false_positive")
    assert fp.error_count == 2


# ---------------------------------------------------------------------------------------------------
# Ranking / dedup / top-K / tie-break
# ---------------------------------------------------------------------------------------------------

def test_ranking_is_deterministic_and_severity_first() -> None:
    a = _sf("a", 0.4, severity="MEDIUM")
    b = _sf("b", 0.9, severity="CRITICAL")
    c = _sf("c", 0.4, severity="MEDIUM")
    ranked = rank_samples([a, b, c])
    # CRITICAL first; then MEDIUM ties broken by sample_id ascending
    assert [s.sample_id for s in ranked] == ["b", "a", "c"]
    assert [s.rank for s in ranked] == [1, 2, 3]


def test_tie_break_error_rate_then_count_then_id() -> None:
    # same severity + rate -> higher count first, then sample_id
    x = _sf("x", 0.5, count=50, severity="HIGH")
    y = _sf("y", 0.5, count=60, severity="HIGH")
    z = _sf("z", 0.5, count=50, severity="HIGH")
    assert [s.sample_id for s in rank_samples([x, y, z])] == ["y", "x", "z"]


def test_dedup_keeps_worst_per_sample() -> None:
    worse = _sf("dup", 0.8, severity="CRITICAL")
    better = _sf("dup", 0.1, severity="LOW")
    deduped = dedup_by_sample([better, worse])
    assert len(deduped) == 1 and deduped[0].error_rate == 0.8


def test_top_k_limits_and_filters() -> None:
    fails = [_sf("a", 0.9, severity="CRITICAL", categories=["class_confusion"]),
             _sf("b", 0.5, severity="HIGH"),
             _sf("c", 0.2, severity="LOW")]
    top2 = top_k(fails, 2, criterion="error_rate")
    assert [h.sample_id for h in top2] == ["a", "b"] and top2[0].rank == 1
    only_confusion = top_k(fails, 5, error_type="class_confusion")
    assert [h.sample_id for h in only_confusion] == ["a"]


# ---------------------------------------------------------------------------------------------------
# Sample-level analysis + stratification + split isolation (numpy)
# ---------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_thin_cloud_and_clear_confusion_visible() -> None:
    from app.evaluation import EvaluationConfig, EvaluationRunner
    ecfg = EvaluationConfig.cloudsen12(split="test")
    t = np.array([0, 1, 2, 2, 3]); p = np.array([0, 1, 0, 0, 3])   # thin(2)->clear(0)
    res = EvaluationRunner(ecfg).run([(t, p)])
    samples = [{"sample_id": "s1", "targets": t, "predictions": p, "group": "A"}]
    out = analyze_failures(CFG, evaluation_result=res, samples=samples)
    thin_sum = next(s for s in out.class_summaries if s.key == "thin_cloud")
    assert thin_sum.total_errors == 2                      # thin-cloud failures directly visible
    assert out.sample_failures[0].dominant_true_class == "thin_cloud"
    assert "thin_cloud_failure" in out.sample_failures[0].categories


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_perfect_sample_is_not_a_failure() -> None:
    from app.evaluation import EvaluationConfig, EvaluationRunner
    ecfg = EvaluationConfig.cloudsen12(split="test")
    t = np.array([0, 1, 2, 3])
    res = EvaluationRunner(ecfg).run([(t, t.copy())])
    out = analyze_failures(CFG, evaluation_result=res,
                           samples=[{"sample_id": "perfect", "targets": t, "predictions": t.copy()}])
    assert out.sample_failures == []


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_split_isolation_enforced() -> None:
    from app.failure_analysis.sample_analysis import analyze_samples
    with pytest.raises(FailureAnalysisError):
        analyze_samples(CFG, [{"sample_id": "x", "targets": np.array([0]),
                               "predictions": np.array([0]), "split": "train"}])


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
def test_group_summaries_present() -> None:
    from app.evaluation import EvaluationConfig, EvaluationRunner
    res = EvaluationRunner(EvaluationConfig.cloudsen12(split="test")).run(
        [(np.array([0, 1, 2, 3]), np.array([0, 0, 2, 3]))])
    samples = [{"sample_id": "a", "targets": np.array([0, 0]), "predictions": np.array([1, 1]),
                "group": "region_a"},
               {"sample_id": "b", "targets": np.array([0, 0]), "predictions": np.array([0, 1]),
                "group": "region_b"}]
    out = analyze_failures(CFG, evaluation_result=res, samples=samples)
    groups = {s.key for s in out.group_summaries}
    assert groups == {"region_a", "region_b"}


# ---------------------------------------------------------------------------------------------------
# Limitations / confidence unavailable / serialization / report / viz
# ---------------------------------------------------------------------------------------------------

def test_limitations_label_unavailable() -> None:
    out = analyze_failures(CFG, confusion=_cm([[5, 0, 0, 0], [0, 5, 0, 0], [0, 0, 5, 0], [0, 0, 0, 5]]))
    text = " ".join(out.limitations)
    assert "NOT MEASURABLE" in text and "DEFERRED" in text and "NOT YET MEASURED" in text
    # confidence is never fabricated
    assert all(e.confidence is None for e in out.pixel_errors)


def test_result_serialization_roundtrip(tmp_path: Path) -> None:
    out = analyze_failures(CFG, confusion=_cm([[5, 0, 0, 0], [0, 5, 0, 0], [2, 0, 3, 0], [0, 0, 0, 5]]))
    assert FailureAnalysisResult.from_json(out.to_json()).config_hash == out.config_hash
    path = out.save_json(tmp_path / "fa.json")
    assert FailureAnalysisResult.load_json(path).to_dict() == out.to_dict()


def test_report_generation(tmp_path: Path) -> None:
    from app.failure_analysis.report import export_failure_report
    out = analyze_failures(CFG, confusion=_cm([[5, 0, 0, 0], [0, 5, 0, 0], [2, 0, 3, 0], [0, 0, 0, 5]]))
    written = export_failure_report(out, tmp_path / "rep", formats=("json", "csv", "md"))
    assert set(written) == {"json", "csv", "md"} and all(p.is_file() for p in written.values())
    md = (tmp_path / "rep.md").read_text()
    assert "Failure taxonomy" in md and "Limitations" in md


def test_visualization_spec_generation() -> None:
    sf = _sf("chip_1", 0.6, severity="HIGH", categories=["thin_cloud_failure"])
    specs = confusing_case_specs(sf, CFG, ground_truth_source=Path("gt.tif"),
                                 prediction_source=Path("pred.tif"), image_source=Path("img.tif"))
    assert set(specs["specs"]) == {"ground_truth", "prediction", "error_overlay"}
    assert specs["specs"]["ground_truth"]["options"]["severity"] == "HIGH"
    assert len(specs["legend"]["entries"]) == 4
