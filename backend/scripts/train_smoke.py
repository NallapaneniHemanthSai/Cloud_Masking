#!/usr/bin/env python3
"""Run a short SYNTHETIC training smoke run (Milestone 7).

Demonstrates experiment execution end-to-end on **synthetic random tensors** — no real dataset, no
evaluation. Builds a baseline model + a `TrainingConfig`, creates an experiment directory, runs a few
epochs, and writes checkpoints/logs + the `ExperimentRun` (run.json). Requires PyTorch; without it, prints
the resolved config and exits.

Usage:
    python backend/scripts/train_smoke.py --epochs 2 --output-dir outputs/experiments
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.models._torch import torch_available  # noqa: E402
from app.training.config import LoggingConfig, LossConfig, TrainingConfig  # noqa: E402
from app.training.experiment import create_experiment  # noqa: E402

logger = logging.getLogger("train_smoke")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run a synthetic training smoke run.")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batches", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", type=Path, default=settings.outputs_dir / "experiments")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    config = TrainingConfig(experiment_name="smoke", epochs=args.epochs, device=args.device,
                            seed=args.seed, loss=LossConfig(name="dice_ce"),
                            logging=LoggingConfig(console=True))
    logger.info("Training config hash: %s", config.config_hash())

    if not torch_available():
        logger.warning("PyTorch unavailable — printing config only (no training run).")
        return 0

    import torch
    from app.models import ModelConfig, ModelFactory
    from app.training import Trainer

    run, paths = create_experiment(config, args.output_dir)
    torch.manual_seed(args.seed)
    g = torch.Generator().manual_seed(args.seed)
    loader = [(torch.rand(2, 4, 16, 16, generator=g), torch.randint(0, 2, (2, 16, 16), generator=g))
              for _ in range(args.batches)]
    model_config = ModelConfig(in_channels=4, num_classes=2, encoder_depth=2, base_channels=8)
    factory = ModelFactory()
    trainer = Trainer(config, factory.create(model_config), loader, output_dir=paths.root)
    summary = trainer.fit()
    logger.info("Trainer lifecycle state: %s", trainer.trainer_state.value)

    run.training_metadata = trainer.training_metadata(run.experiment_id).to_dict()
    for ckpt in sorted(paths.checkpoints.glob("*.pt")):
        run.add_checkpoint(ckpt)
    for log in sorted(paths.logs.glob("*")):
        run.add_log(log)

    # Canonical completed-run metadata (no evaluation/inference/deployment content).
    model_artifact = factory.build_artifact(model_config)
    artifact = trainer.build_training_artifact(run, model_artifact=model_artifact)
    artifact_path = artifact.save_json(paths.artifacts / "training_artifact.json")
    run.add_artifact(artifact_path)
    run.save_json(paths.run)

    logger.info("Experiment: %s", paths.root)
    logger.info("Training artifact: %s (id=%s)", artifact_path, artifact.artifact_id)
    logger.info("Summary: %s", summary.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
