"""Trainer lifecycle state machine (Milestone 7, revised).

A typed :class:`TrainerState` enum with explicit, validated transitions used internally by the trainer.
Standard-library only.

Valid transitions::

    CREATED       -> INITIALIZED | FAILED
    INITIALIZED   -> RUNNING | FAILED
    RUNNING       -> CHECKPOINTING | COMPLETED | FAILED
    CHECKPOINTING -> RUNNING | COMPLETED | FAILED
    COMPLETED     -> (terminal)
    FAILED        -> (terminal)
"""

from __future__ import annotations

import enum

from app.core.exceptions import TrainingError


class TrainerState(enum.Enum):
    """Lifecycle states of a training execution."""

    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    CHECKPOINTING = "checkpointing"
    COMPLETED = "completed"
    FAILED = "failed"


VALID_TRANSITIONS: dict[TrainerState, frozenset[TrainerState]] = {
    TrainerState.CREATED: frozenset({TrainerState.INITIALIZED, TrainerState.FAILED}),
    TrainerState.INITIALIZED: frozenset({TrainerState.RUNNING, TrainerState.FAILED}),
    TrainerState.RUNNING: frozenset(
        {TrainerState.CHECKPOINTING, TrainerState.COMPLETED, TrainerState.FAILED}),
    TrainerState.CHECKPOINTING: frozenset(
        {TrainerState.RUNNING, TrainerState.COMPLETED, TrainerState.FAILED}),
    TrainerState.COMPLETED: frozenset(),
    TrainerState.FAILED: frozenset(),
}


def is_valid_transition(current: TrainerState, target: TrainerState) -> bool:
    """True when ``current -> target`` is an allowed transition."""
    return target in VALID_TRANSITIONS.get(current, frozenset())


class TrainerStateMachine:
    """Tracks the trainer's lifecycle state and enforces valid transitions."""

    def __init__(self) -> None:
        self.state: TrainerState = TrainerState.CREATED
        self.history: list[TrainerState] = [TrainerState.CREATED]

    def transition_to(self, target: TrainerState) -> TrainerState:
        """Transition to ``target`` or raise :class:`TrainingError` if the transition is invalid."""
        if not is_valid_transition(self.state, target):
            raise TrainingError(f"Invalid trainer transition: {self.state.value} -> {target.value}.")
        self.state = target
        self.history.append(target)
        return self.state
