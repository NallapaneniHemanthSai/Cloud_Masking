"""Structured training logging (Milestone 7).

A backend-independent metric-logging abstraction: a :class:`MetricSink` interface with JSONL, CSV, and
console implementations, composed by :class:`TrainingLogger`. **TensorBoard is not integrated** — but the
`MetricSink` interface isolates it so a `TensorBoardSink` can be added later without touching the trainer.
Standard-library only.

NB: this module is ``app.training.logging`` — with absolute imports, ``import logging`` below still refers
to the standard-library logging module.
"""

from __future__ import annotations

import csv
import json
import logging as _stdlogging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

_logger = _stdlogging.getLogger(__name__)


class MetricSink(ABC):
    """Abstract sink that receives structured metric records."""

    @abstractmethod
    def log(self, record: dict[str, Any]) -> None:
        """Write one metric record."""

    def close(self) -> None:  # optional
        """Flush/close any resources."""


class ConsoleSink(MetricSink):
    """Logs records to the standard logging system."""

    def log(self, record: dict[str, Any]) -> None:
        _logger.info("metrics %s", record)


class JsonlSink(MetricSink):
    """Appends one JSON object per line (JSONL)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


class CsvSink(MetricSink):
    """Appends rows to a CSV, writing the header from the first record's keys."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fieldnames: list[str] | None = None

    def log(self, record: dict[str, Any]) -> None:
        write_header = self._fieldnames is None
        if write_header:
            self._fieldnames = list(record.keys())
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow({k: record.get(k, "") for k in self._fieldnames})


class TrainingLogger:
    """Composes multiple sinks; the trainer logs once, all sinks receive the record."""

    def __init__(self, sinks: list[MetricSink] | None = None) -> None:
        self.sinks: list[MetricSink] = sinks or []

    def add_sink(self, sink: MetricSink) -> "TrainingLogger":
        self.sinks.append(sink)
        return self

    def log(self, record: dict[str, Any]) -> None:
        for sink in self.sinks:
            sink.log(record)

    def close(self) -> None:
        for sink in self.sinks:
            sink.close()

    @classmethod
    def from_config(cls, log_dir: Path, formats: tuple[str, ...] = ("json", "csv"),
                    console: bool = True) -> "TrainingLogger":
        """Build a logger with JSONL/CSV/console sinks per the logging config."""
        log_dir = Path(log_dir)
        logger = cls()
        if "json" in formats:
            logger.add_sink(JsonlSink(log_dir / "metrics.jsonl"))
        if "csv" in formats:
            logger.add_sink(CsvSink(log_dir / "metrics.csv"))
        if console:
            logger.add_sink(ConsoleSink())
        return logger
