"""Milestone 7 (revised) verification: callback priorities/events, TrainerState machine, TrainingArtifact.

Synthetic only; no training-loop torch dependency for these tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import TrainingError
from app.training.artifact import TrainingArtifact
from app.training.callbacks import (
    Callback,
    CallbackContext,
    CallbackEvent,
    CallbackList,
    CallbackPriority,
)
from app.training.config import TrainingConfig
from app.training.lifecycle import (
    TrainerState,
    TrainerStateMachine,
    is_valid_transition,
)
from app.training.metadata import CheckpointState, TrainingMetadata, TrainingState


# ---------------------------------------------------------------------------------------------------
# Callback priorities + events
# ---------------------------------------------------------------------------------------------------

class _Tagged(Callback):
    def __init__(self, tag: str, sink: list[str], priority: CallbackPriority) -> None:
        super().__init__(priority)
        self.tag = tag
        self.sink = sink

    def on_epoch_end(self, ctx: CallbackContext) -> None:
        self.sink.append(self.tag)


def test_callbacks_execute_in_priority_order() -> None:
    sink: list[str] = []
    # Registered in a deliberately "wrong" order; must run HIGHEST -> LOWEST.
    cbs = CallbackList([
        _Tagged("lowest", sink, CallbackPriority.LOWEST),
        _Tagged("highest", sink, CallbackPriority.HIGHEST),
        _Tagged("normal", sink, CallbackPriority.NORMAL),
        _Tagged("high", sink, CallbackPriority.HIGH),
    ])
    cbs.dispatch(CallbackEvent.EPOCH_END, CallbackContext(config=TrainingConfig(), state=TrainingState()))
    assert sink == ["highest", "high", "normal", "lowest"]


def test_equal_priority_preserves_registration_order() -> None:
    sink: list[str] = []
    cbs = CallbackList([
        _Tagged("a", sink, CallbackPriority.NORMAL),
        _Tagged("b", sink, CallbackPriority.NORMAL),
        _Tagged("c", sink, CallbackPriority.NORMAL),
    ])
    cbs.dispatch(CallbackEvent.EPOCH_END, CallbackContext(config=TrainingConfig(), state=TrainingState()))
    assert sink == ["a", "b", "c"]


def test_callback_event_enum_values() -> None:
    assert {e.name for e in CallbackEvent} == {
        "TRAIN_START", "EPOCH_START", "BATCH_START", "BATCH_END", "EPOCH_END", "TRAIN_END"}


def test_only_matching_event_handler_runs() -> None:
    sink: list[str] = []
    cb = _Tagged("x", sink, CallbackPriority.NORMAL)
    ctx = CallbackContext(config=TrainingConfig(), state=TrainingState())
    cb.on_event(CallbackEvent.TRAIN_START, ctx)   # no on_train_start override -> nothing
    assert sink == []
    cb.on_event(CallbackEvent.EPOCH_END, ctx)
    assert sink == ["x"]


# ---------------------------------------------------------------------------------------------------
# TrainerState machine
# ---------------------------------------------------------------------------------------------------

def test_valid_transitions() -> None:
    assert is_valid_transition(TrainerState.CREATED, TrainerState.INITIALIZED)
    assert is_valid_transition(TrainerState.INITIALIZED, TrainerState.RUNNING)
    assert is_valid_transition(TrainerState.RUNNING, TrainerState.CHECKPOINTING)
    assert is_valid_transition(TrainerState.CHECKPOINTING, TrainerState.RUNNING)
    assert is_valid_transition(TrainerState.RUNNING, TrainerState.COMPLETED)
    assert is_valid_transition(TrainerState.RUNNING, TrainerState.FAILED)


def test_invalid_transitions() -> None:
    assert not is_valid_transition(TrainerState.CREATED, TrainerState.RUNNING)
    assert not is_valid_transition(TrainerState.COMPLETED, TrainerState.RUNNING)   # terminal
    assert not is_valid_transition(TrainerState.FAILED, TrainerState.RUNNING)      # terminal


def test_state_machine_enforces_transitions() -> None:
    m = TrainerStateMachine()
    assert m.state == TrainerState.CREATED
    m.transition_to(TrainerState.INITIALIZED)
    m.transition_to(TrainerState.RUNNING)
    m.transition_to(TrainerState.CHECKPOINTING)
    m.transition_to(TrainerState.RUNNING)
    m.transition_to(TrainerState.COMPLETED)
    assert m.history[0] == TrainerState.CREATED and m.history[-1] == TrainerState.COMPLETED
    with pytest.raises(TrainingError):
        m.transition_to(TrainerState.RUNNING)   # COMPLETED is terminal


# ---------------------------------------------------------------------------------------------------
# TrainingArtifact
# ---------------------------------------------------------------------------------------------------

def _artifact(created_at: str = "t", notes: str = "n") -> TrainingArtifact:
    exp = {"experiment_id": "exp-123", "name": "exp"}
    meta = TrainingMetadata(experiment_id="exp-123", config_hash="cfg", seed=42)
    ckpt = CheckpointState(epoch=1, global_step=4, metric_value=0.5, config_hash="cfg")
    return TrainingArtifact.create(
        experiment_run=exp, training_metadata=meta, training_config_hash="cfg",
        environment_capture={"python_version": "3.11.0"}, model_artifact={"content_hash": "mh"},
        checkpoint_state=ckpt, created_at=created_at, notes=notes)


def test_training_artifact_deterministic_hash_and_id() -> None:
    a = _artifact()
    b = _artifact(created_at="different", notes="other")   # created_at/notes excluded from hash
    assert a.content_hash() == b.content_hash()
    assert a.artifact_id == b.artifact_id and a.artifact_id.startswith("train-")
    # a different config hash changes the content hash
    exp = {"experiment_id": "exp-123"}
    meta = TrainingMetadata(experiment_id="exp-123")
    c = TrainingArtifact.create(experiment_run=exp, training_metadata=meta,
                                training_config_hash="OTHER")
    assert c.content_hash() != a.content_hash()


def test_training_artifact_serialization_roundtrip(tmp_path: Path) -> None:
    a = _artifact()
    assert TrainingArtifact.from_dict(a.to_dict()).content_hash() == a.content_hash()
    assert TrainingArtifact.from_json(a.to_json()).artifact_id == a.artifact_id
    path = a.save_json(tmp_path / "artifact.json")
    loaded = TrainingArtifact.load_json(path)
    assert loaded.artifact_id == a.artifact_id
    assert "content_hash" in a.to_dict()


def test_training_artifact_metadata_integrity() -> None:
    a = _artifact()
    d = a.to_dict()
    assert d["experiment_run"]["experiment_id"] == "exp-123"
    assert d["training_metadata"]["seed"] == 42
    assert d["checkpoint_state"]["metric_value"] == 0.5
    assert d["model_artifact"]["content_hash"] == "mh"
    # no evaluation/inference/deployment keys leak in
    for forbidden in ("metrics", "predictions", "deployment", "inference"):
        assert forbidden not in d
