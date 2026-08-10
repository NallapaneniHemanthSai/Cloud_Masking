"""Augmentation framework (Milestone 4, revised) — backend-agnostic.

Infrastructure only — augmentation is NOT performed during training here. The framework exposes **generic**
augmentation operations (``Flip``, ``Rotate``, ``Crop``, ``Brightness``, ``Contrast``) and an
:class:`AugmentationPipeline`, all independent of any third-party library. A separate
:class:`AlbumentationsAdapter` translates the generic operations into Albumentations transforms *only when
that library is available* — Albumentations classes never leak into the preprocessing API.

The registry, generic operations, spec parsing, and pipeline are standard-library (unit-testable); the
adapter imports ``albumentations`` lazily and raises a clear error if it is missing.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from typing import Any, Callable, ClassVar

from app.core.constants import AugmentationOp
from app.core.exceptions import PreprocessingError

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------------------
# Generic (backend-agnostic) augmentation operations.
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class AugmentationOperation:
    """Base class for generic augmentation operations."""

    p: float = 0.5
    NAME: ClassVar[str] = "operation"

    def params(self) -> dict[str, Any]:
        """Return this operation's parameters as a plain dict."""
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.NAME, "params": self.params()}


@dataclass(frozen=True)
class Flip(AugmentationOperation):
    """Random horizontal/vertical flip."""

    NAME: ClassVar[str] = AugmentationOp.FLIP.value


@dataclass(frozen=True)
class Rotate(AugmentationOperation):
    """Random rotation within +/- ``limit`` degrees."""

    limit: int = 90
    NAME: ClassVar[str] = AugmentationOp.ROTATE.value


@dataclass(frozen=True)
class Crop(AugmentationOperation):
    """Random crop to ``height`` x ``width``."""

    p: float = 1.0
    height: int = 256
    width: int = 256
    NAME: ClassVar[str] = AugmentationOp.CROP.value


@dataclass(frozen=True)
class Brightness(AugmentationOperation):
    """Random brightness adjustment by +/- ``limit``."""

    limit: float = 0.2
    NAME: ClassVar[str] = AugmentationOp.BRIGHTNESS.value


@dataclass(frozen=True)
class Contrast(AugmentationOperation):
    """Random contrast adjustment by +/- ``limit``."""

    limit: float = 0.2
    NAME: ClassVar[str] = AugmentationOp.CONTRAST.value


@dataclass(frozen=True)
class AugmentationSpec:
    """A configured augmentation operation (name + params) parsed from config."""

    name: str
    params: dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_any(cls, item: Any) -> "AugmentationSpec":
        if isinstance(item, str):
            return cls(name=item)
        if isinstance(item, dict) and "name" in item:
            return cls(name=str(item["name"]), params=dict(item.get("params", {})))
        raise PreprocessingError(f"Invalid augmentation spec: {item!r}")


@dataclass
class AugmentationPipeline:
    """An ordered, backend-agnostic sequence of generic augmentation operations."""

    operations: list[AugmentationOperation] = dataclasses.field(default_factory=list)
    enabled: bool = True

    def names(self) -> list[str]:
        return [op.NAME for op in self.operations]

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "operations": [op.to_dict() for op in self.operations]}


# --------------------------------------------------------------------------------------------------
# Registry mapping op names -> factories that build GENERIC operations (no third-party dependency).
# --------------------------------------------------------------------------------------------------

OperationFactory = Callable[[dict[str, Any]], AugmentationOperation]


class AugmentationRegistry:
    """Registry mapping operation names to generic-operation factories."""

    def __init__(self) -> None:
        self._factories: dict[str, OperationFactory] = {}

    def register(self, name: str, factory: OperationFactory, *, overwrite: bool = False) -> None:
        if not overwrite and name in self._factories:
            raise PreprocessingError(f"Augmentation '{name}' is already registered.")
        self._factories[name] = factory

    def get(self, name: str) -> OperationFactory:
        if name not in self._factories:
            raise PreprocessingError(
                f"Unknown augmentation '{name}'. Registered: {sorted(self._factories)}."
            )
        return self._factories[name]

    def list_ops(self) -> list[str]:
        return sorted(self._factories)

    def __contains__(self, name: object) -> bool:
        return name in self._factories

    def build_operation(self, spec: AugmentationSpec) -> AugmentationOperation:
        return self.get(spec.name)(spec.params)

    def build(self, specs: list[AugmentationSpec]) -> list[AugmentationOperation]:
        return [self.build_operation(s) for s in specs]


def _flip(params: dict[str, Any]) -> AugmentationOperation:
    return Flip(p=params.get("p", 0.5))


def _rotate(params: dict[str, Any]) -> AugmentationOperation:
    return Rotate(limit=params.get("limit", 90), p=params.get("p", 0.5))


def _crop(params: dict[str, Any]) -> AugmentationOperation:
    size = params.get("size")
    return Crop(height=params.get("height", size or 256),
                width=params.get("width", size or 256), p=params.get("p", 1.0))


def _brightness(params: dict[str, Any]) -> AugmentationOperation:
    return Brightness(limit=params.get("limit", 0.2), p=params.get("p", 0.5))


def _contrast(params: dict[str, Any]) -> AugmentationOperation:
    return Contrast(limit=params.get("limit", 0.2), p=params.get("p", 0.5))


_BUILTIN_FACTORIES: dict[str, OperationFactory] = {
    AugmentationOp.FLIP.value: _flip,
    AugmentationOp.ROTATE.value: _rotate,
    AugmentationOp.CROP.value: _crop,
    AugmentationOp.BRIGHTNESS.value: _brightness,
    AugmentationOp.CONTRAST.value: _contrast,
}


def default_registry() -> AugmentationRegistry:
    """Return a registry pre-populated with the built-in generic operations."""
    registry = AugmentationRegistry()
    for name, factory in _BUILTIN_FACTORIES.items():
        registry.register(name, factory)
    return registry


def build_pipeline(specs: list[AugmentationSpec], enabled: bool = True,
                   registry: AugmentationRegistry | None = None) -> AugmentationPipeline:
    """Build a backend-agnostic :class:`AugmentationPipeline` from specs (no Albumentations)."""
    registry = registry or default_registry()
    operations = registry.build(specs) if enabled else []
    logger.info("Built generic augmentation pipeline with %d operation(s) (enabled=%s).",
                len(operations), enabled)
    return AugmentationPipeline(operations=operations, enabled=enabled)


# --------------------------------------------------------------------------------------------------
# Albumentations adapter — the ONLY place that references albumentations.
# --------------------------------------------------------------------------------------------------

def _require_albumentations():  # returns the module
    try:
        import albumentations as A  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise PreprocessingError(
            "albumentations is required to build Albumentations transforms but is not installed. "
            "Install project dependencies (see requirements.in) in the Python 3.11 environment."
        ) from exc
    return A


class AlbumentationsAdapter:
    """Translates generic augmentation operations into Albumentations transforms (lazily)."""

    def to_transform(self, op: AugmentationOperation) -> Any:
        """Translate a single generic operation to an Albumentations transform."""
        A = _require_albumentations()
        if isinstance(op, Flip):
            return A.Flip(p=op.p)
        if isinstance(op, Rotate):
            return A.Rotate(limit=op.limit, p=op.p)
        if isinstance(op, Crop):
            return A.RandomCrop(height=op.height, width=op.width, p=op.p)
        if isinstance(op, Brightness):
            return A.RandomBrightnessContrast(brightness_limit=op.limit, contrast_limit=0.0, p=op.p)
        if isinstance(op, Contrast):
            return A.RandomBrightnessContrast(brightness_limit=0.0, contrast_limit=op.limit, p=op.p)
        raise PreprocessingError(f"No Albumentations translation for operation {op!r}.")

    def to_compose(self, pipeline: AugmentationPipeline) -> Any:
        """Translate a whole pipeline to an ``albumentations.Compose`` (no-op when disabled)."""
        A = _require_albumentations()
        transforms = [self.to_transform(op) for op in pipeline.operations] if pipeline.enabled else []
        return A.Compose(transforms)
