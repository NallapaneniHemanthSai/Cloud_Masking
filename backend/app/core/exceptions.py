"""Typed exception hierarchy for the Cloud Masking backend (SCAFFOLD).

Provides a single base exception so call sites can catch project errors without resorting to bare
``except:`` blocks (a coding-standard requirement). Concrete raising sites are added in later milestones.
"""

from __future__ import annotations


class CloudMaskingError(Exception):
    """Base class for all project-specific errors."""


class ConfigurationError(CloudMaskingError):
    """Raised when configuration is missing, malformed, or inconsistent."""


class DatasetError(CloudMaskingError):
    """Raised for dataset acquisition/validation problems (schema, CRS, bands, provenance)."""


class PreprocessingError(CloudMaskingError):
    """Raised for failures in the preprocessing pipeline (bands, indices, tiling, augmentation)."""


class ModelError(CloudMaskingError):
    """Raised for model construction, loading, or checkpoint errors."""


class InferenceError(CloudMaskingError):
    """Raised for prediction/inference failures."""


class EvaluationError(CloudMaskingError):
    """Raised for evaluation/metric computation failures."""


class GuardrailViolation(CloudMaskingError):
    """Raised when a KPI guardrail is violated (e.g., an aggregate hides a failing subgroup).

    Central to the negative-test campaign (NT-1..NT-5); wired to degraded mode in later milestones.
    """
