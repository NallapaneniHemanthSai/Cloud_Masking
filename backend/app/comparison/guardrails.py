"""Fairness guardrails (Milestone 11).

Detects **accidental** differences between the two comparison arms. A controlled comparison is only valid
when the model architecture/config is the *sole* intentional difference; every other control (dataset,
preprocessing, split, seed, loss, optimizer, scheduler, batch size, training budget, augmentation,
normalization, …) must match. :func:`check_fairness` compares the two arms' fairness signatures field by
field, reports **all** compared fields, and (in strict mode) raises :class:`GuardrailViolation` on any
mismatch. Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.comparison.config import ComparisonConfig, ExperimentPlan
from app.core.exceptions import GuardrailViolation

#: Top-level shared controls that must match (nested dicts are compared recursively / by leaf path).
FAIRNESS_FIELDS: tuple[str, ...] = (
    "seed",
    "training.epochs", "training.batch_size", "training.grad_accum_steps", "training.device",
    "training.seed", "training.deterministic", "training.mixed_precision", "training.init_strategy",
    "training.max_grad_norm", "training.optimizer", "training.scheduler", "training.loss",
    "training.early_stopping", "training.checkpoint", "training.logging",
    "evaluation.mode", "evaluation.num_classes", "evaluation.class_names", "evaluation.ignore_index",
    "evaluation.dataset", "evaluation.split",
    "failure.dataset", "failure.split", "failure.mode", "failure.class_names", "failure.top_k",
    "failure.ignore_index", "failure.severity_thresholds",
)


@dataclass
class FieldComparison:
    """The comparison outcome for one fairness field."""

    field: str
    baseline: Any
    improved: Any
    matches: bool

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "baseline": self.baseline, "improved": self.improved,
                "matches": self.matches}


@dataclass
class FairnessReport:
    """Result of a fairness check across the two arms (reports ALL compared fields)."""

    passed: bool
    compared: list[FieldComparison] = field(default_factory=list)
    mismatches: list[FieldComparison] = field(default_factory=list)
    intended_difference: str = "model architecture/config"
    baseline_model: dict[str, Any] = field(default_factory=dict)
    improved_model: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def compared_fields(self) -> list[str]:
        return [c.field for c in self.compared]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "intended_difference": self.intended_difference,
            "compared_fields": self.compared_fields,
            "compared": [c.to_dict() for c in self.compared],
            "mismatches": [c.to_dict() for c in self.mismatches],
            "baseline_model": self.baseline_model,
            "improved_model": self.improved_model,
            "notes": self.notes,
        }


def _resolve(signature: dict[str, Any], dotted: str) -> Any:
    """Resolve a dotted path (e.g. ``training.optimizer``) within a fairness signature."""
    node: Any = signature
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def check_fairness(baseline: ExperimentPlan, improved: ExperimentPlan, *,
                   strict: bool = True) -> FairnessReport:
    """Compare two arms field-by-field; report all fields and (strict) raise on any mismatch.

    The models themselves are the *intended* difference and are recorded but never compared for equality.
    """
    base_sig = baseline.fairness_signature()
    impr_sig = improved.fairness_signature()

    compared: list[FieldComparison] = []
    mismatches: list[FieldComparison] = []
    for dotted in FAIRNESS_FIELDS:
        b = _resolve(base_sig, dotted)
        i = _resolve(impr_sig, dotted)
        fc = FieldComparison(field=dotted, baseline=b, improved=i, matches=(b == i))
        compared.append(fc)
        if not fc.matches:
            mismatches.append(fc)

    # A real comparison also requires the architectures to actually differ.
    same_arch = baseline.model.config_hash() == improved.model.config_hash()
    report = FairnessReport(
        passed=(not mismatches and not same_arch), compared=compared, mismatches=mismatches,
        baseline_model=baseline.model.to_dict(), improved_model=improved.model.to_dict(),
        notes=("Model architecture/config is the only intended difference. "
               + ("WARNING: both arms share the same model config." if same_arch else "")))

    if strict and not report.passed:
        if same_arch:
            raise GuardrailViolation(
                "Fairness violation: both comparison arms use the same model config "
                "(no architectural difference to attribute results to).")
        detail = "; ".join(f"{m.field}: baseline={m.baseline!r} != improved={m.improved!r}"
                           for m in mismatches)
        raise GuardrailViolation(f"Fairness violation — non-architectural controls differ: {detail}")
    return report


def check_config_fairness(config: ComparisonConfig, *, seed: int | None = None,
                          strict: bool = True) -> FairnessReport:
    """Convenience: derive both arms from a :class:`ComparisonConfig` and check them."""
    baseline, improved = config.plans(seed=seed)
    return check_fairness(baseline, improved, strict=strict)
