"""Milestone 17 verification: deployment / containerization configuration.

Runs under pytest AND standalone (``python backend/tests/test_deployment.py``). Framework-free.

These are **static** checks over the committed deployment surface (Dockerfiles, Compose, nginx
template, pinned requirements, .dockerignore). They deliberately do NOT need a Docker daemon, so the
deployment contract stays verifiable on any machine and in CI; the *live* container behaviour is
verified separately by ``backend/scripts/verify_deployment.py`` against a running stack.

No real data, no network, no fabricated metric.
"""

from __future__ import annotations

import re
import sys
from contextlib import contextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKER_DIR = PROJECT_ROOT / "docker"

BACKEND_DOCKERFILE = DOCKER_DIR / "backend.Dockerfile"
FRONTEND_DOCKERFILE = DOCKER_DIR / "frontend.Dockerfile"
COMPOSE_FILE = DOCKER_DIR / "docker-compose.yml"
NGINX_TEMPLATE = DOCKER_DIR / "nginx.conf.template"
REQUIREMENTS = DOCKER_DIR / "requirements-backend.txt"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"


@contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type:
        return
    except Exception as other:  # noqa: BLE001
        raise AssertionError(f"expected {exc_type.__name__}, got {type(other).__name__}: {other}")
    raise AssertionError(f"expected {exc_type.__name__}, but no exception was raised")


def _read(path: Path) -> str:
    assert path.is_file(), f"missing deployment file: {path.relative_to(PROJECT_ROOT)}"
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------------
# Files exist
# --------------------------------------------------------------------------------------------------
def test_deployment_files_exist() -> None:
    for path in (BACKEND_DOCKERFILE, FRONTEND_DOCKERFILE, COMPOSE_FILE,
                 NGINX_TEMPLATE, REQUIREMENTS, DOCKERIGNORE):
        assert path.is_file(), f"missing: {path}"


def test_milestone2_placeholders_are_gone() -> None:
    """The M2 placeholder images must be replaced, not merely annotated."""
    for path in (BACKEND_DOCKERFILE, FRONTEND_DOCKERFILE, COMPOSE_FILE):
        text = _read(path)
        assert "PLACEHOLDER" not in text.upper() or "placeholder\"]" not in text, \
            f"{path.name} still looks like the M2 placeholder"
        assert 'profiles: ["placeholder"]' not in text, f"{path.name} still has the placeholder profile"


# --------------------------------------------------------------------------------------------------
# Backend image
# --------------------------------------------------------------------------------------------------
def test_backend_image_pins_python_311() -> None:
    """ADR-0004: the geo/ML stack is Python 3.11.x only."""
    text = _read(BACKEND_DOCKERFILE)
    assert re.search(r"^FROM python:3\.11-slim", text, re.M), "backend image must pin python:3.11-slim"
    assert "python:3.12" not in text and "python:3.14" not in text


def test_backend_image_runs_as_non_root() -> None:
    text = _read(BACKEND_DOCKERFILE)
    assert re.search(r"^USER\s+appuser", text, re.M), "backend image must drop to a non-root user"
    assert re.search(r"useradd .*appuser", text), "backend image must create the non-root user"
    # The USER directive must come before the process is started.
    assert text.index("USER appuser") < text.index("CMD ["), "USER must precede CMD"


def test_backend_image_has_healthcheck_and_exposes_port() -> None:
    text = _read(BACKEND_DOCKERFILE)
    assert "HEALTHCHECK" in text, "backend image must define a HEALTHCHECK"
    assert "/health" in text, "the healthcheck must probe the /health endpoint"
    assert re.search(r"^EXPOSE\s+8000", text, re.M)


def test_backend_entrypoint_reuses_the_project_launcher() -> None:
    """M17 packages what exists — it must not introduce a second server entry point."""
    text = _read(BACKEND_DOCKERFILE)
    assert "scripts/serve_api.py" in text, "backend image must launch via the M13 serve_api.py launcher"
    assert (PROJECT_ROOT / "backend/scripts/serve_api.py").is_file()


def test_backend_configuration_is_environment_driven() -> None:
    """Config comes from env vars with defaults — never a hard-coded host path."""
    text = _read(BACKEND_DOCKERFILE)
    for var in ("API_HOST=", "API_PORT=", "LOG_LEVEL=", "OUTPUTS_DIR=", "DATABASE_URL="):
        assert var in text, f"backend image must define {var} as an overridable ENV default"
    assert "API_HOST=0.0.0.0" in text, "the container must bind all interfaces"
    # The CMD must not re-hard-code host/port, or the env vars become decorative.
    cmd = re.search(r"^CMD \[(.*)\]", text, re.M)
    assert cmd, "backend image must define a CMD"
    assert "--host" not in cmd.group(1) and "--port" not in cmd.group(1), \
        "CMD must take host/port from API_HOST/API_PORT, not hard-coded flags"
    assert "/Users/" not in text and "/home/hemanth" not in text, "no absolute host paths in the image"


# --------------------------------------------------------------------------------------------------
# Pinned dependencies (Risk R-12 / R-09)
# --------------------------------------------------------------------------------------------------
def _requirement_lines() -> list[str]:
    return [ln.strip() for ln in _read(REQUIREMENTS).splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def test_every_backend_dependency_is_exactly_pinned() -> None:
    """R-09 (reproducibility drift): a clean-env rebuild must resolve to the same versions."""
    for line in _requirement_lines():
        assert "==" in line, f"dependency is not exactly pinned: {line!r}"
        assert not line.startswith("-"), f"unexpected pip flag in a pinned file: {line!r}"


def test_geo_stack_is_pinned_for_r12() -> None:
    """R-12: GDAL/rasterio system deps must not drift between host and container."""
    lines = _requirement_lines()
    assert any(ln.lower().startswith("rasterio==") for ln in lines), \
        "rasterio (bundled GDAL) must be pinned in the backend image — Risk R-12"


def test_deployed_runtime_covers_every_api_capability() -> None:
    """The image must be able to serve /train and /predict, not just the torch-free endpoints."""
    lines = [ln.lower() for ln in _requirement_lines()]
    for pkg in ("fastapi==", "uvicorn", "sqlalchemy==", "pydantic==", "numpy==", "torch=="):
        assert any(ln.startswith(pkg) for ln in lines), f"missing pinned runtime dependency: {pkg}"


def test_backend_image_installs_gdal_system_libs_for_r12() -> None:
    """R-12: rasterio's wheel bundles GDAL but still links base system libs absent from slim.

    Without libexpat1, `import rasterio` dies with `libexpat.so.1: cannot open shared object file`.
    """
    text = _read(BACKEND_DOCKERFILE)
    assert "libexpat1" in text, "python:3.11-slim needs libexpat1 for rasterio/GDAL — Risk R-12"
    assert "rm -rf /var/lib/apt/lists/*" in text, "apt lists must be cleaned in the same layer"


def test_backend_image_asserts_its_own_imports_at_build_time() -> None:
    """A missing system lib must fail the build, not surface as a 500 at runtime."""
    text = _read(BACKEND_DOCKERFILE)
    assert "import torch, rasterio, fastapi, sqlalchemy" in text, \
        "the build must prove the runtime imports work inside the image"


def test_torch_is_installed_from_the_cpu_index() -> None:
    """No CUDA payload: containers run CPU-only here (MPS is host-only, ADR-0002)."""
    text = _read(BACKEND_DOCKERFILE)
    assert "download.pytorch.org/whl/cpu" in text, \
        "torch must come from the CPU wheel index, or pip pulls ~445 MB of unusable nvidia-* wheels"
    assert re.search(r"--index-url \$\{TORCH_INDEX_URL\}", text), \
        "the CPU index must be used as the primary index for the torch install"
    assert "find_spec('nvidia')" in text, \
        "the build should assert no CUDA payload was pulled in"


def test_dataset_acquisition_is_not_shipped_in_the_image() -> None:
    """A deployment image must not be able to pull CloudSEN12+ (ADR-0012 access policy)."""
    lines = [ln.lower() for ln in _requirement_lines()]
    assert not any(ln.startswith("tacoreader") for ln in lines), \
        "tacoreader (dataset acquisition) must not be installed in the deployment image"


def test_pinned_versions_match_the_verified_host_environment() -> None:
    """Pins are captured from the venv M13-M16 were verified against, not invented."""
    pins = dict(ln.split("==", 1) for ln in _requirement_lines())
    normalized = {k.split("[")[0].lower(): v for k, v in pins.items()}
    assert normalized.get("torch") == "2.13.0"
    assert normalized.get("numpy") == "1.26.4"
    assert normalized.get("rasterio") == "1.4.4"
    assert normalized.get("fastapi") == "0.115.14"


# --------------------------------------------------------------------------------------------------
# Frontend image + nginx proxy (ADR-0014 contract)
# --------------------------------------------------------------------------------------------------
def test_frontend_image_is_multistage_node_to_nginx() -> None:
    text = _read(FRONTEND_DOCKERFILE)
    assert re.search(r"^FROM node:20-alpine AS build", text, re.M), "stage 1 must be node:20-alpine"
    assert re.search(r"^FROM nginx:1\.27-alpine", text, re.M), "stage 2 must be a pinned nginx"
    assert "npm ci" in text, "must install from the committed lockfile"
    assert "npm run build" in text, "must run the typecheck+build script"
    assert "--from=build /app/dist" in text, "must copy the built bundle into the serve stage"


def test_frontend_image_has_healthcheck() -> None:
    text = _read(FRONTEND_DOCKERFILE)
    assert "HEALTHCHECK" in text and "/healthz" in text


def test_nginx_proxy_strips_the_api_prefix_like_vite() -> None:
    """Production must reproduce the Vite dev-proxy rewrite exactly, or the SPA breaks."""
    text = _read(NGINX_TEMPLATE)
    assert "location ^~ /api/" in text, "nginx must handle the /api prefix"
    assert re.search(r"rewrite\s+\^/api/\(\.\*\)\$\s+/\$1\s+break;", text), \
        "nginx must strip the /api prefix before proxying (mirrors vite.config.ts)"
    assert "proxy_pass" in text

    vite = _read(PROJECT_ROOT / "frontend/vite.config.ts")
    assert "'/api'" in vite and "replace(/^\\/api/, '')" in vite, \
        "the Vite dev proxy contract changed — the nginx rewrite must be kept in step"


def test_nginx_reresolves_the_backend_for_restart_survival() -> None:
    """A static upstream pins the IP nginx saw at boot and breaks after `restart backend`."""
    text = _read(NGINX_TEMPLATE)
    assert "resolver 127.0.0.11" in text, "nginx needs Docker's embedded DNS resolver"
    assert re.search(r"set \$cm_backend .*BACKEND_HOST", text), \
        "the upstream must be a variable so nginx re-resolves it at request time"
    assert "proxy_pass $cm_backend" in text


def test_nginx_serves_the_spa_fallback() -> None:
    text = _read(NGINX_TEMPLATE)
    assert "try_files $uri $uri/ /index.html" in text, "client-side routes need the SPA fallback"


def test_nginx_upstream_is_environment_driven() -> None:
    text = _read(NGINX_TEMPLATE)
    assert "${BACKEND_HOST}" in text and "${BACKEND_PORT}" in text, \
        "the backend address must be env-substituted, not hard-coded"
    fe = _read(FRONTEND_DOCKERFILE)
    assert "NGINX_ENVSUBST_FILTER" in fe, \
        "envsubst must be filtered so nginx's own $variables survive rendering"


# --------------------------------------------------------------------------------------------------
# Compose stack
# --------------------------------------------------------------------------------------------------
def _compose_text() -> str:
    return _read(COMPOSE_FILE)


def test_compose_defines_backend_and_frontend() -> None:
    text = _compose_text()
    assert re.search(r"^  backend:", text, re.M)
    assert re.search(r"^  frontend:", text, re.M)
    assert "dockerfile: docker/backend.Dockerfile" in text
    assert "dockerfile: docker/frontend.Dockerfile" in text


def test_compose_gates_startup_on_backend_health() -> None:
    """The frontend must not start before the API is actually ready."""
    text = _compose_text()
    assert "depends_on:" in text
    assert "condition: service_healthy" in text, "startup order must be health-gated, not just ordered"
    assert "healthcheck:" in text


def test_compose_puts_services_on_an_explicit_private_network() -> None:
    text = _compose_text()
    assert re.search(r"^networks:", text, re.M), "the stack must declare an explicit network"
    assert "driver: bridge" in text
    assert text.count("- cloud-masking\n") >= 2, "both services must join the network"


def test_compose_persists_state_on_a_named_volume() -> None:
    """Requirement §6 / ADR-0013: SQLite state must outlive the container."""
    text = _compose_text()
    assert re.search(r"^volumes:\s*$", text, re.M), "a named volume must be declared"
    assert "cloud-masking-data:/data" in text, "the backend must mount the state volume at /data"
    assert "sqlite:////data/cloud_masking.db" in text, \
        "DATABASE_URL must point at the mounted volume (absolute sqlite path)"


def test_compose_ports_are_environment_driven_with_defaults() -> None:
    text = _compose_text()
    assert "${BACKEND_PORT:-8000}:8000" in text
    assert "${FRONTEND_PORT:-8080}:80" in text


def test_compose_points_the_proxy_at_the_backend_service() -> None:
    text = _compose_text()
    assert 'BACKEND_HOST: "backend"' in text, "the proxy must target the backend service DNS name"
    assert 'BACKEND_PORT: "8000"' in text


# --------------------------------------------------------------------------------------------------
# Build context / security
# --------------------------------------------------------------------------------------------------
def test_dockerignore_keeps_the_build_context_source_only() -> None:
    """A clean-env rebuild must not depend on (or ship) local state."""
    text = _read(DOCKERIGNORE)
    for pattern in ("**/.venv/", "**/node_modules/", "outputs/", "data/raw/", ".git/"):
        assert pattern in text, f".dockerignore must exclude {pattern}"


def test_no_secrets_in_the_deployment_surface() -> None:
    """No credential may be baked into an image or committed config."""
    secret_like = re.compile(
        r"(password|passwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9/+_-]{6,}",
        re.I)
    for path in (BACKEND_DOCKERFILE, FRONTEND_DOCKERFILE, COMPOSE_FILE, NGINX_TEMPLATE,
                 REQUIREMENTS, PROJECT_ROOT / ".env.example"):
        text = _read(path)
        hit = secret_like.search(text)
        assert hit is None, f"possible secret in {path.name}: {hit.group(0)!r}"
        assert "BEGIN PRIVATE KEY" not in text and "BEGIN RSA" not in text


def test_env_example_documents_the_deployment_variables_without_secrets() -> None:
    text = _read(PROJECT_ROOT / ".env.example")
    for var in ("BACKEND_PORT", "FRONTEND_PORT"):
        assert var in text, f".env.example must document {var}"


# --------------------------------------------------------------------------------------------------
# Earlier-milestone semantics must be untouched by M17
# --------------------------------------------------------------------------------------------------
def test_m17_did_not_change_the_api_contract() -> None:
    """M17 packages the API; it must not add, rename, or remove a route."""
    main_src = _read(PROJECT_ROOT / "backend/app/main.py")
    for module in ("system", "models", "training", "prediction", "evaluation",
                   "history", "upload", "status", "acceptance"):
        assert module in main_src, f"router {module} disappeared from the app factory"


def test_m17_did_not_weaken_the_negative_tests() -> None:
    """NT-1..NT-5 must still all be present and passing in the M16 harness."""
    from app.acceptance import run_acceptance
    report = run_acceptance()
    assert len(report.nt_results) == 5, "expected NT-1..NT-5"
    assert all(nt.passed for nt in report.nt_results), "an NT regressed during M17"
    assert report.safety_passed is True
    assert report.kpi_overall == "NOT_YET_MEASURED", \
        "M17 must not turn unmeasured KPIs into measured ones"


def test_m17_preserved_the_m11_mixed_conclusion() -> None:
    """The bounded real-data verdict is evidence, not something deployment may restate."""
    report = _read(PROJECT_ROOT / "docs/comparison/real_experiment_cloudsen12.md")
    assert "MIXED" in report, "the M11 real-data conclusion must remain MIXED"


def test_deployment_version_constant_is_registered() -> None:
    from app.core import constants as C
    assert C.DEPLOYMENT_VERSION == "0.17.0"


# --------------------------------------------------------------------------------------------------
# Standalone manual harness (pytest is not installed in this project's venv)
# --------------------------------------------------------------------------------------------------
def _run_all() -> int:
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn(); passed += 1; print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1; print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
