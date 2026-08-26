"""In-process request telemetry (Milestone 13).

A tiny, thread-safe registry of per-route request counts / errors / latency, exposed at ``/metrics``. The
FastAPI timing middleware (in :func:`app.main.create_app`) feeds it. Standard-library only — no third-party
dependency, so this stays import-clean and testable without a running server.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TelemetryRegistry:
    """Aggregates per-route latency/counters for the ``/metrics`` endpoint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start = time.time()
        self._routes: dict[str, dict[str, float]] = {}
        self.total_requests = 0
        self.total_errors = 0

    def record(self, route: str, seconds: float, *, error: bool = False) -> None:
        with self._lock:
            self.total_requests += 1
            if error:
                self.total_errors += 1
            r = self._routes.setdefault(route, {"count": 0.0, "error_count": 0.0,
                                                 "total_seconds": 0.0, "last_seconds": 0.0})
            r["count"] += 1
            r["error_count"] += 1 if error else 0
            r["total_seconds"] += seconds
            r["last_seconds"] = seconds

    def uptime_seconds(self) -> float:
        return round(time.time() - self._start, 6)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            routes = []
            for route, r in sorted(self._routes.items()):
                count = int(r["count"]) or 1
                routes.append({
                    "route": route, "count": int(r["count"]), "error_count": int(r["error_count"]),
                    "total_seconds": round(r["total_seconds"], 6),
                    "avg_seconds": round(r["total_seconds"] / count, 6),
                    "last_seconds": round(r["last_seconds"], 6),
                })
            return {"uptime_seconds": self.uptime_seconds(), "total_requests": self.total_requests,
                    "total_errors": self.total_errors, "routes": routes}

    def reset(self) -> None:
        with self._lock:
            self._routes.clear()
            self.total_requests = 0
            self.total_errors = 0
            self._start = time.time()


_REGISTRY = TelemetryRegistry()


def get_registry() -> TelemetryRegistry:
    """Process-wide telemetry registry."""
    return _REGISTRY
