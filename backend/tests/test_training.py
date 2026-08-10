"""Milestone 7 verification: training engine (synthetic data only, no real dataset).

Config/serialization/registry/callback/reproducibility tests run on a bare interpreter; the actual
training-loop tests require torch and are skipped otherwise.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from app.core.exceptions import ConfigurationError, TrainingError
from app.models._torch import torch_available
from app.training.callbacks import (
    Callback,
    CallbackContext,
    CallbackEvent,
    CallbackList,
    EarlyStoppingCallback,
    LoggingCallback,
)
from app.training.checkpoint import CheckpointManager
from app.training.config import (
    CheckpointConfig,
    EarlyStoppingConfig,
    LoggingConfig,
    LossConfig,
    OptimizerConfig,
    SchedulerConfig,
    TrainingConfig,
)
from app.training.experiment import ExperimentRun, create_experiment, experiment_id_for
from app.training.logging import CsvSink, JsonlSink, TrainingLogger
from app.training.metadata import (
    CheckpointState,
    TrainerSummary,
    TrainingMetadata,
    TrainingState,
)
from app.training.optimizer import build_optimizer, list_optimizers
from app.training.scheduler import build_scheduler, list_schedulers, steps_on_metric
from app.training.seed import capture_environment, resolve_device, set_seed

HAS_TORCH = torch_available()


# ---------------------------------------------------------------------------------------------------
# Config + deterministic hashing + serialization
# ---------------------------------------------------------------------------------------------------

def test_training_config_validation() -> None:
    with pytest.raises(ConfigurationError):
        TrainingConfig(epochs=0)
    with pytest.raises(ConfigurationError):
        TrainingConfig(grad_accum_steps=0)
    with pytest.raises(ConfigurationError):
        TrainingConfig(checkpoint=CheckpointConfig(mode="sideways"))


def test_training_config_hash_and_roundtrip() -> None:
    a = TrainingConfig(experiment_name="x", epochs=5)
    b = TrainingConfig(experiment_name="x", epochs=5)
    assert a.config_hash() == b.config_hash()
    assert a.config_hash() != TrainingConfig(experiment_name="x", epochs=6).config_hash()
    restored = TrainingConfig.from_dict(a.to_dict())
    assert restored.to_dict() == a.to_dict()
    assert restored.config_hash() == a.config_hash()


# ---------------------------------------------------------------------------------------------------
# Registries (selection is config-driven; unknown names raise before touching torch)
# ---------------------------------------------------------------------------------------------------

def test_registries_list_expected_names() -> None:
    assert set(list_optimizers()) == {"adam", "adamw", "sgd"}
    assert set(list_schedulers()) == {"cosine", "step", "plateau"}


def test_unknown_optimizer_and_scheduler_raise() -> None:
    with pytest.raises(TrainingError):
        build_optimizer([], OptimizerConfig(name="rmsprop"))
    with pytest.raises(TrainingError):
        build_scheduler(object(), SchedulerConfig(name="magic"), epochs=10)
    # 'none' scheduler returns None without torch
    assert build_scheduler(object(), SchedulerConfig(name="none"), epochs=10) is None
    assert steps_on_metric(SchedulerConfig(name="plateau")) is True


# ---------------------------------------------------------------------------------------------------
# Metadata serialization
# ---------------------------------------------------------------------------------------------------

def test_metadata_dataclasses_serialize() -> None:
    st = TrainingState(epoch=2, global_step=8, best_metric=0.3, monitor="train_loss")
    assert st.to_dict()["best_metric"] == 0.3
    ck = CheckpointState(epoch=1, global_step=4, metric_value=0.5, config_hash="h")
    assert CheckpointState.from_dict(ck.to_dict()).to_dict() == ck.to_dict()
    assert CheckpointState.from_json(ck.to_json()).epoch == 1
    meta = TrainingMetadata(experiment_id="e", seed=42, device="cpu")
    assert TrainingMetadata.from_dict(meta.to_dict()).to_dict() == meta.to_dict()
    summ = TrainerSummary(experiment_id="e", epochs_planned=3, epochs_run=3, best_metric=0.1)
    assert summ.to_dict()["epochs_run"] == 3


# ---------------------------------------------------------------------------------------------------
# Experiment management
# ---------------------------------------------------------------------------------------------------

def test_experiment_run_roundtrip_and_layout(tmp_path: Path) -> None:
    cfg = TrainingConfig(experiment_name="exp", epochs=2)
    run, paths = create_experiment(cfg, tmp_path)
    assert run.experiment_id == experiment_id_for(cfg)
    assert paths.config.is_file() and paths.checkpoints.is_dir() and paths.logs.is_dir()
    run.add_checkpoint(paths.checkpoints / "best.pt")
    p = run.save_json(paths.run)
    assert ExperimentRun.load_json(p).experiment_id == run.experiment_id
    assert ExperimentRun.from_dict(run.to_dict()).to_dict() == run.to_dict()


# ---------------------------------------------------------------------------------------------------
# Checkpoint manager (metadata-only path needs no torch)
# ---------------------------------------------------------------------------------------------------

def test_checkpoint_manager_policy_and_metadata(tmp_path: Path) -> None:
    cm = CheckpointManager(tmp_path, monitor="train_loss", mode="min", save_weights=False)
    assert cm.is_improvement(1.0) is True
    cm.best_value = 0.5
    assert cm.is_improvement(0.4) is True and cm.is_improvement(0.6) is False
    state = CheckpointState(epoch=0, global_step=1, metric_value=0.4, config_hash="h")
    meta_path = cm.maybe_save_best({}, state, value=0.4)   # improves over None best
    assert meta_path is not None and meta_path.is_file()
    reloaded = cm.resume_metadata("best")
    assert reloaded.metric_value == 0.4 and reloaded.has_model_weights is False


# ---------------------------------------------------------------------------------------------------
# Callbacks (execute without torch)
# ---------------------------------------------------------------------------------------------------

class _Recorder(Callback):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def on_train_start(self, ctx): self.calls.append("train_start")
    def on_epoch_start(self, ctx): self.calls.append("epoch_start")
    def on_batch_end(self, ctx): self.calls.append("batch_end")
    def on_epoch_end(self, ctx): self.calls.append("epoch_end")
    def on_train_end(self, ctx): self.calls.append("train_end")


def test_callback_event_dispatch_order() -> None:
    rec = _Recorder()
    cbs = CallbackList([rec])
    ctx = CallbackContext(config=TrainingConfig(), state=TrainingState())
    for event in (CallbackEvent.TRAIN_START, CallbackEvent.EPOCH_START, CallbackEvent.BATCH_END,
                  CallbackEvent.EPOCH_END, CallbackEvent.TRAIN_END):
        cbs.dispatch(event, ctx)
    assert rec.calls == ["train_start", "epoch_start", "batch_end", "epoch_end", "train_end"]


def test_early_stopping_triggers() -> None:
    cb = EarlyStoppingCallback(EarlyStoppingConfig(enabled=True, monitor="train_loss",
                                                   mode="min", patience=2))
    ctx = CallbackContext(config=TrainingConfig(), state=TrainingState())
    for value in (1.0, 0.9, 1.0, 1.0):   # improves, improves, then 2 no-improvements
        ctx.metrics = {"train_loss": value}
        cb.on_epoch_end(ctx)
    assert ctx.state.stop_requested is True


def test_logging_callback_writes_record(tmp_path: Path) -> None:
    logger = TrainingLogger([JsonlSink(tmp_path / "m.jsonl")])
    ctx = CallbackContext(config=TrainingConfig(), state=TrainingState(epoch=1, global_step=3),
                          metrics={"train_loss": 0.7}, logger=logger)
    LoggingCallback().on_epoch_end(ctx)
    line = json.loads((tmp_path / "m.jsonl").read_text().strip())
    assert line["epoch"] == 1 and line["train_loss"] == 0.7


# ---------------------------------------------------------------------------------------------------
# Logging sinks
# ---------------------------------------------------------------------------------------------------

def test_logging_sinks_write_files(tmp_path: Path) -> None:
    logger = TrainingLogger([JsonlSink(tmp_path / "a.jsonl"), CsvSink(tmp_path / "a.csv")])
    logger.log({"epoch": 0, "train_loss": 1.0})
    logger.log({"epoch": 1, "train_loss": 0.5})
    assert len((tmp_path / "a.jsonl").read_text().strip().splitlines()) == 2
    assert len((tmp_path / "a.csv").read_text().strip().splitlines()) == 3   # header + 2 rows


# ---------------------------------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------------------------------

def test_set_seed_is_deterministic() -> None:
    set_seed(123)
    a = [random.random() for _ in range(3)]
    set_seed(123)
    b = [random.random() for _ in range(3)]
    assert a == b


def test_capture_environment_and_resolve_device() -> None:
    env = capture_environment().to_dict()
    assert set(env) >= {"python_version", "platform", "cuda_available", "mps_available"}
    assert resolve_device("cpu") == "cpu"
    assert resolve_device("auto") in {"cpu", "cuda", "mps"}


# ---------------------------------------------------------------------------------------------------
# Trainer end-to-end (requires torch; synthetic data only)
# ---------------------------------------------------------------------------------------------------

def _synthetic_loader():
    import torch
    g = torch.Generator().manual_seed(123)
    return [(torch.rand(2, 4, 16, 16, generator=g), torch.randint(0, 2, (2, 16, 16), generator=g))
            for _ in range(3)]


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_trainer_fit_synthetic(tmp_path: Path) -> None:
    import torch
    from app.models import ModelConfig, ModelFactory
    from app.training import Trainer

    torch.manual_seed(0)
    model = ModelFactory().create(ModelConfig(in_channels=4, num_classes=2, encoder_depth=2,
                                              base_channels=8))
    cfg = TrainingConfig(experiment_name="t", epochs=2, grad_accum_steps=2, device="cpu",
                         optimizer=OptimizerConfig(name="adamw"), scheduler=SchedulerConfig(name="cosine"),
                         loss=LossConfig(name="dice_ce"), logging=LoggingConfig(console=False))
    summary = Trainer(cfg, model, _synthetic_loader(), output_dir=tmp_path).fit()
    assert summary.epochs_run == 2 and summary.best_metric is not None
    assert (tmp_path / "checkpoints" / "best.pt").is_file()
    assert (tmp_path / "logs" / "metrics.jsonl").is_file()


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_trainer_is_deterministic() -> None:
    import torch
    from app.models import ModelConfig, ModelFactory
    from app.training import Trainer

    def run() -> float:
        torch.manual_seed(0)
        model = ModelFactory().create(ModelConfig(in_channels=4, num_classes=2, encoder_depth=2,
                                                  base_channels=8))
        cfg = TrainingConfig(experiment_name="d", epochs=2, device="cpu", seed=7,
                             loss=LossConfig(name="cross_entropy"), logging=LoggingConfig(console=False))
        return Trainer(cfg, model, _synthetic_loader()).fit().final_metrics["train_loss"]

    assert abs(run() - run()) < 1e-9


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_optimizer_and_scheduler_build_with_torch() -> None:
    import torch
    model = torch.nn.Conv2d(3, 4, 3)
    opt = build_optimizer(model.parameters(), OptimizerConfig(name="sgd", lr=0.01))
    assert opt.__class__.__name__ == "SGD"
    sched = build_scheduler(opt, SchedulerConfig(name="step", params={"step_size": 1}), epochs=5)
    assert sched.__class__.__name__ == "StepLR"
