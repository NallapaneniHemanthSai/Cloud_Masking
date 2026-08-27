#!/usr/bin/env python3
"""Deployment verification CLI (Milestone 17 — Docker / clean environment).

Probes a **running** Cloud Masking stack and reports, check by check, whether the deployment
contract holds: backend health/version, API connectivity, frontend delivery, the frontend -> backend
`/api` proxy, environment-driven configuration, and SQLite persistence on the mounted volume.

It is a *black-box* probe — standard library only (``urllib``), no test framework, no Docker SDK — so
it runs against the Compose stack, a host-run ``serve_api.py``, or any other deployment. It never
trains on real data, never downloads a dataset, and never fabricates a metric: everything it exercises
is the bounded **SYNTHETIC / DEMO** path the API already defines (M13-M16).

Exit code is 0 only when every selected check passes, so it can gate CI or a release.

Usage:
    python backend/scripts/verify_deployment.py \
        --api-url http://localhost:8000 --frontend-url http://localhost:8080
    python backend/scripts/verify_deployment.py --api-url http://localhost:8000 --skip-frontend
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_FRONTEND_URL = "http://localhost:8080"

#: Status vocabulary — deliberately the same honest labels the rest of the project uses.
PASS = "VERIFIED"
FAIL = "NOT VERIFIED"
SKIP = "SKIPPED"


# --------------------------------------------------------------------------------------------------
# Result records
# --------------------------------------------------------------------------------------------------
@dataclass
class CheckResult:
    """One deployment check: what was required, what was observed, and the evidence for it."""

    name: str
    status: str
    requirement: str
    observed: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (PASS, SKIP)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "requirement": self.requirement,
            "observed": self.observed,
            "evidence": self.evidence,
        }


# --------------------------------------------------------------------------------------------------
# Minimal HTTP helpers (stdlib only)
# --------------------------------------------------------------------------------------------------
def _request(url: str, *, method: str = "GET", body: dict | None = None,
             timeout: float = 30.0) -> tuple[int, str]:
    """Perform one HTTP request. Returns ``(status_code, text)``; HTTP errors are returned, not raised."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _get_json(url: str, timeout: float = 30.0) -> tuple[int, Any]:
    code, text = _request(url, timeout=timeout)
    try:
        return code, json.loads(text)
    except json.JSONDecodeError:
        return code, text


def wait_for_health(api_url: str, timeout_s: float = 120.0, interval_s: float = 2.0) -> bool:
    """Poll ``/health`` until it answers 200 or the timeout elapses (startup gate)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            code, _ = _request(f"{api_url}/health", timeout=5.0)
            if code == 200:
                return True
        except OSError:
            pass
        time.sleep(interval_s)
    return False


# --------------------------------------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------------------------------------
def check_backend_health(api_url: str) -> CheckResult:
    req = "GET /health returns 200 with a status/device/database snapshot."
    try:
        code, body = _get_json(f"{api_url}/health")
    except OSError as exc:
        return CheckResult("backend health", FAIL, req, f"unreachable: {exc}")
    if code != 200 or not isinstance(body, dict) or body.get("status") != "ok":
        return CheckResult("backend health", FAIL, req, f"HTTP {code}: {body!r}"[:300])
    return CheckResult("backend health", PASS, req,
                       f"status=ok device={body.get('device')} torch={body.get('torch_available')}",
                       {"health": body})


def check_backend_version(api_url: str) -> CheckResult:
    req = "GET /version returns every component version from app.core.constants."
    required = ("app_version", "model_version", "evaluation_version", "python")
    try:
        code, body = _get_json(f"{api_url}/version")
    except OSError as exc:
        return CheckResult("backend version", FAIL, req, f"unreachable: {exc}")
    if code != 200 or not isinstance(body, dict):
        return CheckResult("backend version", FAIL, req, f"HTTP {code}")
    missing = [k for k in required if not body.get(k)]
    if missing:
        return CheckResult("backend version", FAIL, req, f"missing fields: {missing}")
    return CheckResult("backend version", PASS, req,
                       f"app={body['app_version']} python={body['python']} torch={body.get('torch')}",
                       {"version": body})


def check_api_connectivity(api_url: str) -> CheckResult:
    """Every contract endpoint the deployed system must answer (M13-M16 routes)."""
    req = "All M13-M16 read endpoints answer 200 (API contract preserved)."
    routes = ["/version", "/health", "/metrics", "/models", "/history",
              "/status", "/lineage", "/acceptance", "/openapi.json", "/docs"]
    results: dict[str, int] = {}
    for route in routes:
        try:
            code, _ = _request(f"{api_url}{route}", timeout=60.0)
        except OSError as exc:
            results[route] = -1
            _ = exc
        else:
            results[route] = code
    bad = {r: c for r, c in results.items() if c != 200}
    if bad:
        return CheckResult("API connectivity", FAIL, req, f"non-200: {bad}", {"routes": results})
    return CheckResult("API connectivity", PASS, req,
                       f"{len(routes)}/{len(routes)} routes returned 200", {"routes": results})


def check_frontend(frontend_url: str) -> CheckResult:
    req = "The SPA is served (index.html with the app root) and nginx reports healthy."
    try:
        code, text = _request(frontend_url, timeout=30.0)
    except OSError as exc:
        return CheckResult("frontend delivery", FAIL, req, f"unreachable: {exc}")
    if code != 200:
        return CheckResult("frontend delivery", FAIL, req, f"HTTP {code}")
    if 'id="root"' not in text or "<script" not in text:
        return CheckResult("frontend delivery", FAIL, req, "response is not the built SPA shell")
    return CheckResult("frontend delivery", PASS, req,
                       f"index.html served ({len(text)} bytes, app root + bundle present)",
                       {"bytes": len(text)})


def check_frontend_to_backend(frontend_url: str) -> CheckResult:
    """The production proxy must reproduce the Vite dev rewrite: /api/<path> -> backend /<path>."""
    req = "Frontend proxies /api/* to the backend, stripping the /api prefix (ADR-0014 contract)."
    try:
        code, body = _get_json(f"{frontend_url}/api/health")
        vcode, vbody = _get_json(f"{frontend_url}/api/version")
    except OSError as exc:
        return CheckResult("frontend -> backend", FAIL, req, f"unreachable: {exc}")
    if code != 200 or not isinstance(body, dict) or body.get("status") != "ok":
        return CheckResult("frontend -> backend", FAIL, req, f"/api/health HTTP {code}: {body!r}"[:300])
    if vcode != 200 or not isinstance(vbody, dict) or not vbody.get("app_version"):
        return CheckResult("frontend -> backend", FAIL, req, f"/api/version HTTP {vcode}")
    return CheckResult("frontend -> backend", PASS, req,
                       f"/api/health ok; /api/version app={vbody['app_version']} (prefix stripped)",
                       {"api_health": body, "app_version": vbody["app_version"]})


def check_env_configuration(api_url: str) -> CheckResult:
    """Configuration must come from the environment, not from a baked-in path."""
    req = "Runtime configuration is environment-driven (DATABASE_URL visible via /health)."
    try:
        code, body = _get_json(f"{api_url}/health")
    except OSError as exc:
        return CheckResult("env configuration", FAIL, req, f"unreachable: {exc}")
    if code != 200 or not isinstance(body, dict):
        return CheckResult("env configuration", FAIL, req, f"HTTP {code}")
    database = str(body.get("database", ""))
    if not database:
        return CheckResult("env configuration", FAIL, req, "no database URL reported")
    return CheckResult("env configuration", PASS, req,
                       f"DATABASE_URL in effect: {database}", {"database": database})


def check_persistence(api_url: str) -> CheckResult:
    """Write through the API, then read it back — proves the mounted SQLite volume is live.

    Uses the API's bounded **SYNTHETIC** evaluation path. No real data, no fabricated KPI.
    """
    req = "A SYNTHETIC evaluation persists to SQLite and is readable through /history."
    try:
        before_code, before = _get_json(f"{api_url}/history?limit=200", timeout=60.0)
        if before_code != 200 or not isinstance(before, dict):
            return CheckResult("persistence", FAIL, req, f"/history HTTP {before_code}")
        n_before = len(before.get("evaluations", []))

        code, body = _request(f"{api_url}/evaluate", method="POST",
                              body={"synthetic": True, "seed": 17}, timeout=180.0)
        if code != 200:
            return CheckResult("persistence", FAIL, req, f"POST /evaluate HTTP {code}: {body[:200]}")
        evaluation_id = json.loads(body).get("evaluation_id", "")

        after_code, after = _get_json(f"{api_url}/history?limit=200", timeout=60.0)
        if after_code != 200 or not isinstance(after, dict):
            return CheckResult("persistence", FAIL, req, f"/history HTTP {after_code}")
        n_after = len(after.get("evaluations", []))
    except OSError as exc:
        return CheckResult("persistence", FAIL, req, f"unreachable: {exc}")

    if n_after <= n_before:
        return CheckResult("persistence", FAIL, req,
                           f"evaluation rows did not grow ({n_before} -> {n_after})")
    return CheckResult("persistence", PASS, req,
                       f"SYNTHETIC evaluation {evaluation_id[:12]} persisted "
                       f"({n_before} -> {n_after} rows)",
                       {"evaluations_before": n_before, "evaluations_after": n_after,
                        "evaluation_id": evaluation_id, "data_label": "SYNTHETIC"})


def check_history_survived(api_url: str, expected_min: int) -> CheckResult:
    """After a restart, previously-written rows must still be there (volume, not container, state)."""
    req = "Persisted rows survive a container restart (state lives on the volume)."
    try:
        code, body = _get_json(f"{api_url}/history?limit=200", timeout=60.0)
    except OSError as exc:
        return CheckResult("restart persistence", FAIL, req, f"unreachable: {exc}")
    if code != 200 or not isinstance(body, dict):
        return CheckResult("restart persistence", FAIL, req, f"HTTP {code}")
    n = len(body.get("evaluations", []))
    if n < expected_min:
        return CheckResult("restart persistence", FAIL, req,
                           f"expected >= {expected_min} evaluation rows after restart, found {n}")
    return CheckResult("restart persistence", PASS, req,
                       f"{n} evaluation rows still present (>= {expected_min} written before restart)",
                       {"evaluations": n, "expected_min": expected_min})


def check_acceptance(api_url: str) -> CheckResult:
    """The M16 D5 harness must still report NT-1..NT-5 as it does on the host."""
    req = "GET /acceptance reports the D5 harness verdict with all five NTs (M16 unchanged)."
    try:
        code, body = _get_json(f"{api_url}/acceptance", timeout=120.0)
    except OSError as exc:
        return CheckResult("M16 acceptance (deployed)", FAIL, req, f"unreachable: {exc}")
    if code != 200 or not isinstance(body, dict):
        return CheckResult("M16 acceptance (deployed)", FAIL, req, f"HTTP {code}")
    nts = body.get("nt_results") or body.get("negative_tests") or []
    passed = [n for n in nts if isinstance(n, dict) and n.get("passed")]
    if len(nts) != 5 or len(passed) != 5:
        return CheckResult("M16 acceptance (deployed)", FAIL, req,
                           f"{len(passed)}/{len(nts)} NTs passed (expected 5/5)", {"acceptance": body})
    return CheckResult("M16 acceptance (deployed)", PASS, req,
                       f"NT-1..NT-5 = 5/5 PASS on SYNTHETIC fixtures; "
                       f"safety={body.get('safety_passed')} kpi={body.get('kpi_overall')}",
                       {"safety_passed": body.get("safety_passed"),
                        "kpi_overall": body.get("kpi_overall"),
                        "overall": body.get("overall")})


# --------------------------------------------------------------------------------------------------
# Runner / reporting
# --------------------------------------------------------------------------------------------------
def run_checks(api_url: str, frontend_url: str | None,
               restart_expect: int | None = None) -> list[CheckResult]:
    """Run the deployment checks and return their results in report order."""
    results: list[CheckResult] = []
    checks: list[Callable[[], CheckResult]] = [
        lambda: check_backend_health(api_url),
        lambda: check_backend_version(api_url),
        lambda: check_api_connectivity(api_url),
        lambda: check_env_configuration(api_url),
        lambda: check_persistence(api_url),
        lambda: check_acceptance(api_url),
    ]
    if frontend_url:
        checks.append(lambda: check_frontend(frontend_url))
        checks.append(lambda: check_frontend_to_backend(frontend_url))
    else:
        results.append(CheckResult("frontend delivery", SKIP, "SPA is served", "--skip-frontend"))
        results.append(CheckResult("frontend -> backend", SKIP, "/api proxy", "--skip-frontend"))
    if restart_expect is not None:
        checks.append(lambda: check_history_survived(api_url, restart_expect))

    for check in checks:
        results.append(check())
    return results


def print_report(results: list[CheckResult]) -> None:
    """Print a human-readable verification matrix."""
    width = max(len(r.name) for r in results) + 2
    print()
    print("=== Deployment verification (M17) ===")
    for r in results:
        print(f"  [{r.status:<12}] {r.name:<{width}} {r.observed}")
    failed = [r for r in results if not r.ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed"
          f"{'' if not failed else ' — FAILED: ' + ', '.join(r.name for r in failed)}")
    print("NOTE: everything exercised here is the bounded SYNTHETIC/DEMO path. No real-data KPI is "
          "produced; formal KPIs remain NOT YET MEASURED and the M11 conclusion remains MIXED.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify a running Cloud Masking deployment (M17).")
    p.add_argument("--api-url", default=DEFAULT_API_URL, help="Backend base URL.")
    p.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL, help="Frontend base URL.")
    p.add_argument("--skip-frontend", action="store_true", help="Only probe the backend.")
    p.add_argument("--wait", type=float, default=0.0,
                   help="Seconds to wait for /health before starting (0 = do not wait).")
    p.add_argument("--restart-expect", type=int, default=None,
                   help="Assert at least N evaluation rows survive (post-restart persistence check).")
    p.add_argument("--json", type=Path, default=None, help="Also write the results as JSON here.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    api_url = args.api_url.rstrip("/")
    frontend_url = None if args.skip_frontend else args.frontend_url.rstrip("/")

    if args.wait > 0 and not wait_for_health(api_url, timeout_s=args.wait):
        print(f"[{FAIL}] backend did not become healthy at {api_url} within {args.wait:.0f}s")
        return 1

    results = run_checks(api_url, frontend_url, restart_expect=args.restart_expect)
    print_report(results)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
        print(f"JSON report: {args.json}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
