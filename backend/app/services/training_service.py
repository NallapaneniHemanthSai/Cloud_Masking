"""Training service (Milestone 13).

Runs a **bounded** training execution through the reused M7 `Trainer` (no second training engine) and
persists a :class:`TrainingRunRow`. Defaults to small **synthetic** data (labelled ``SYNTHETIC``) so the
endpoint is fast and needs no real dataset. Requires torch; without it a clear :class:`TrainingError` is
raised (the router maps that to 503). Real/full-dataset training and the AC-4 benchmark are out of scope.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import TrainingError
from app.db.base import Database
from app.db.models import TrainingRunRow


def run_training(db: Database, *, architecture: str = "unet", in_channels: int = 13, num_classes: int = 4,
                 encoder_depth: int = 2, base_channels: int = 8, epochs: int = 1, batch_size: int = 2,
                 seed: int = 42, device: str = "cpu", synthetic: bool = True, synthetic_patch: int = 16,
                 synthetic_batches: int = 2) -> dict[str, Any]:
    """Execute a bounded training run and persist its record."""
    from app.models._torch import torch_available
    if not torch_available():
        raise TrainingError("PyTorch is required for /train but is not available in this environment.")
    if not synthetic:
        raise TrainingError("Only synthetic bounded training is exposed via the API (real/AC-4 training "
                            "runs are out of M13 scope). Set synthetic=true.")

    import torch

    from app.models import ModelConfig, ModelFactory
    from app.models.summary import count_parameters
    from app.training import Trainer
    from app.training.config import TrainingConfig

    model_config = ModelConfig(name=architecture, in_channels=in_channels, num_classes=num_classes,
                               encoder_depth=encoder_depth, base_channels=base_channels)
    training_config = TrainingConfig(experiment_name=f"api-{architecture}", epochs=epochs,
                                     batch_size=batch_size, device=device, seed=seed)
    model = ModelFactory().create(model_config)

    g = torch.Generator().manual_seed(seed)
    loader = []
    for _ in range(synthetic_batches):
        x = torch.rand(batch_size, in_channels, synthetic_patch, synthetic_patch, generator=g)
        y = x[:, :num_classes].argmax(dim=1).long()
        loader.append((x, y))

    trainer = Trainer(training_config, model, loader)
    summary = trainer.fit()
    params, _ = count_parameters(model)

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    final_loss = summary.final_metrics.get("train_loss") if summary.final_metrics else None
    with db.session() as s:
        row = TrainingRunRow(
            run_id=run_id, experiment_id=summary.experiment_id, architecture=architecture,
            training_config_hash=training_config.config_hash(), dataset="synthetic",
            dataset_version="", data_regime="SYNTHETIC", seed=seed, device=trainer.device,
            epochs=epochs, status="completed", duration_seconds=summary.duration_seconds,
            best_metric=summary.best_metric, final_loss=final_loss,
            notes="SYNTHETIC / VALIDATION ONLY — bounded API training (not a benchmark).")
        s.add(row)
        s.flush()
        out = row.to_dict()
    out["parameter_count"] = params
    out["training_config_hash"] = training_config.config_hash()
    return out
