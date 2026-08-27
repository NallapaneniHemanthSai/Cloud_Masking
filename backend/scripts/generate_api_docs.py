#!/usr/bin/env python3
"""Generate the REST API reference from the OpenAPI schema (Milestone 18 / D6).

The API reference is **generated, never hand-written**: it imports ``app.main.create_app()`` and renders
``app.openapi()`` to Markdown. The code is therefore the single source of truth, and a DTO change shows
up as a diff in the generated page instead of silently rotting (ADR-0018).

No running server is needed — the app factory is imported directly — so this works in CI and in a clean
checkout.

Usage:
    python backend/scripts/generate_api_docs.py                       # write docs/api/README.md
    python backend/scripts/generate_api_docs.py --check               # fail if the file is out of date
    python backend/scripts/generate_api_docs.py --output some/path.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

DEFAULT_OUTPUT = _PROJECT_ROOT / "docs" / "api" / "README.md"

#: Endpoints grouped in the order a reader meets them, keyed by the OpenAPI tag.
TAG_ORDER = ["system", "models", "training", "prediction", "evaluation",
             "history", "upload", "integration", "acceptance"]

TAG_BLURB = {
    "system": "Liveness, component versions and in-process telemetry (M13).",
    "models": "The model registry: available architectures and recorded model versions (M6/M10/M13).",
    "training": "Bounded **SYNTHETIC** training through the M7 trainer. Never a benchmark run (M13).",
    "prediction": "Inference through the M6 models + M4 preprocessing (M13).",
    "evaluation": "Metrics through the M8 evaluation engine (M13).",
    "history": "Persisted training runs, predictions, evaluations and uploads (M13).",
    "upload": "Raster upload into the git-ignored uploads directory, content-hashed (M13).",
    "integration": "System status, degraded mode + recovery, NT-5 lineage, and the masking pipeline (M15).",
    "acceptance": "The D5 acceptance harness verdict — NT-1..NT-5 on SYNTHETIC fixtures (M16).",
}


def _schema() -> dict[str, Any]:
    """Build the app and return its OpenAPI document."""
    from app.main import create_app
    return create_app().openapi()


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _type_of(prop: dict[str, Any]) -> str:
    """Render a JSON-schema property as a short, readable type string."""
    if "$ref" in prop:
        return f"[`{_ref_name(prop['$ref'])}`](#{_ref_name(prop['$ref']).lower()})"
    if "anyOf" in prop:
        return " \\| ".join(_type_of(p) for p in prop["anyOf"])
    kind = prop.get("type", "any")
    if kind == "array":
        return f"array<{_type_of(prop.get('items', {}))}>"
    if kind == "object" and "additionalProperties" in prop:
        inner = prop["additionalProperties"]
        return f"object<{_type_of(inner) if isinstance(inner, dict) else 'any'}>"
    return f"`{kind}`"


def _schema_cell(schema: dict[str, Any] | None) -> str | None:
    """Render a request/response schema, including inline (non-$ref) ones.

    An endpoint typed as a bare ``dict`` has no ``$ref``; rendering that as "—" would wrongly imply
    it takes no body, so fall back to the inline JSON-schema type.
    """
    if not schema:
        return None
    if "$ref" in schema:
        name = _ref_name(schema["$ref"])
        return f"[`{name}`](#{name.lower()})"
    if schema.get("type") == "object":
        return "free-form `object`"
    if schema.get("type"):
        return _type_of(schema)
    return None


def _body_cell(op: dict[str, Any]) -> str | None:
    for media in ((op.get("requestBody") or {}).get("content") or {}).values():
        cell = _schema_cell(media.get("schema"))
        if cell:
            return cell
    return None


def _response_cell(op: dict[str, Any]) -> str | None:
    ok = (op.get("responses") or {}).get("200") or {}
    for media in (ok.get("content") or {}).values():
        cell = _schema_cell(media.get("schema"))
        if cell:
            return cell
    return None


def _render_endpoints(doc: dict[str, Any]) -> list[str]:
    by_tag: dict[str, list[tuple[str, str, dict]]] = {}
    for path, ops in doc.get("paths", {}).items():
        for method, op in ops.items():
            tag = (op.get("tags") or ["other"])[0]
            by_tag.setdefault(tag, []).append((method.upper(), path, op))

    lines: list[str] = ["## Endpoints", ""]
    total = sum(len(v) for v in by_tag.values())
    lines += [f"{total} operations across {len(by_tag)} groups. "
              "Swagger UI is live at `/docs` and the raw schema at `/openapi.json`.", ""]

    for tag in TAG_ORDER + [t for t in sorted(by_tag) if t not in TAG_ORDER]:
        if tag not in by_tag:
            continue
        lines += [f"### `{tag}`", "", TAG_BLURB.get(tag, ""), "",
                  "| Method | Path | Request body | Response |", "|---|---|---|---|"]
        for method, path, op in sorted(by_tag[tag], key=lambda x: x[1]):
            params = op.get("parameters") or []
            body_cell = _body_cell(op) or (
                ", ".join(f"`{p['name']}`" for p in params) or "—")
            if params and _body_cell(op):
                body_cell += " + " + ", ".join(f"`{p['name']}`" for p in params)
            lines.append(f"| `{method}` | `{path}` | {body_cell} | {_response_cell(op) or '—'} |")
        lines.append("")
    return lines


def _render_schemas(doc: dict[str, Any]) -> list[str]:
    schemas = (doc.get("components") or {}).get("schemas") or {}
    lines = ["## Data models", "",
             f"{len(schemas)} Pydantic v2 DTOs (`backend/app/schemas/api.py`). "
             "Fields marked **required** must be supplied.", ""]
    for name in sorted(schemas):
        s = schemas[name]
        lines += [f"### `{name}`", ""]
        if s.get("description"):
            lines += [s["description"], ""]
        props = s.get("properties") or {}
        if not props:
            lines += ["_No fields._", ""]
            continue
        required = set(s.get("required") or [])
        lines += ["| Field | Type | Required | Default |", "|---|---|---|---|"]
        for field, prop in props.items():
            default = prop.get("default")
            default_cell = "—" if default is None else f"`{default}`"
            lines.append(f"| `{field}` | {_type_of(prop)} | "
                         f"{'yes' if field in required else 'no'} | {default_cell} |")
        lines.append("")
    return lines


def render(doc: dict[str, Any]) -> str:
    """Render the whole API reference. Deterministic: no timestamps, stable ordering."""
    info = doc.get("info", {})
    lines = [
        f"# API Reference — {info.get('title', 'API')} v{info.get('version', '?')}",
        "",
        "> **GENERATED FILE — do not edit by hand.**",
        "> Produced from the live OpenAPI schema by `backend/scripts/generate_api_docs.py`",
        "> (ADR-0018). Regenerate after any router or DTO change:",
        ">",
        "> ```bash",
        "> backend/.venv/bin/python backend/scripts/generate_api_docs.py",
        "> ```",
        "",
        info.get("description", ""),
        "",
        "## Conventions",
        "",
        "- **Base URL.** Direct: `http://localhost:8000`. Through the frontend (dev *and* Docker):",
        "  `http://localhost:8080/api` — the `/api` prefix is stripped before the request reaches the",
        "  backend, so `/api/health` here is `/health` there (ADR-0014 / ADR-0017).",
        "- **Content type.** JSON, except `POST /upload` (`multipart/form-data`).",
        "- **Errors.** Domain failures return `{\"detail\": str, \"error_type\": str}` with **422**;",
        "  a torch-only action attempted without PyTorch returns **503**; an unknown recovery event",
        "  returns **404**. Validation errors use FastAPI's standard **422** body.",
        "- **Authentication.** None. The API is unauthenticated by design and is intended for local /",
        "  single-host operation only (ADR-0013 non-scope, ADR-0017 limitations).",
        "",
        "> **Honesty:** every result this API produces from its default paths is",
        "> **SYNTHETIC / VALIDATION ONLY** or **DEMO**. `POST /train` and `POST /evaluate` use bounded synthetic",
        "> tensors and are **not** benchmarks; `POST /predict` on an untrained model returns a structural",
        "> mask, not a measurement. No formal KPI is served by any endpoint — they remain **NOT YET",
        "> MEASURED** — and the bounded M11 real-data conclusion remains **MIXED**.",
        "",
    ]
    lines += _render_endpoints(doc)
    lines += _render_schemas(doc)
    lines += [
        "## Related documentation",
        "",
        "- [User guide](../user_guide/README.md) — what these endpoints do for a person using the app.",
        "- [Developer guide](../developer_guide/README.md) — how a router reaches the M6–M16 services.",
        "- [Deployment guide](../deployment/README.md) — running the API in Docker.",
        "- [ADR-0013](../adr/ADR-0013-backend-api.md) — why the API is shaped this way.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate the API reference from the OpenAPI schema.")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--check", action="store_true",
                   help="Do not write; exit non-zero if the committed file is out of date.")
    args = p.parse_args(argv)

    content = render(_schema())

    if args.check:
        if not args.output.is_file():
            print(f"MISSING: {args.output}")
            return 1
        if args.output.read_text(encoding="utf-8") != content:
            print(f"OUT OF DATE: {args.output}\nRegenerate with: "
                  f"python backend/scripts/generate_api_docs.py")
            return 1
        print(f"UP TO DATE: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote {args.output} ({len(content.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
