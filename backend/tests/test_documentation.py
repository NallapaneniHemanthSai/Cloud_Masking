"""Milestone 18 verification: documentation completeness & consistency.

Runs under pytest AND standalone (``python backend/tests/test_documentation.py``). Framework-free.

M18's exit criterion is "**Docs complete & consistent**". M1's `09_CONSISTENCY_AUDIT.md` established
that criterion as a *point-in-time manual audit*, which is accurate the day it is written and quietly
less true every day after. These tests make the same criterion **executable**, so doc rot fails a check
instead of being discovered by a reviewer (ADR-0018).

They verify structure, not prose quality: that every required document exists, every relative link
resolves, every referenced ADR/script/config exists, and that no document silently promotes an
unmeasured result. Accuracy of the writing still needs a human.

No network, no Docker, no real data.
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
DOCS = PROJECT_ROOT / "docs"

#: Every document the M18 milestone row and D6 name, plus the guides M1-M17 produced.
REQUIRED_DOCS = [
    "docs/README.md",
    "docs/MANIFEST.md",
    "docs/install/README.md",
    "docs/user_guide/README.md",
    "docs/developer_guide/README.md",
    "docs/api/README.md",
    "docs/deployment/README.md",
    "docs/datasets/README.md",
    "docs/acceptance/README.md",
    "docs/integration/README.md",
    "docs/comparison/real_experiment_cloudsen12.md",
    "docs/adr/ADR-0018-documentation-and-release-packaging.md",
    "docs/planning/10_DOCUMENTATION_AUDIT.md",
    "README.md",
    "backend/README.md",
    "frontend/README.md",
]

#: Markdown files whose relative links must all resolve.
def _all_markdown() -> list[Path]:
    skip = {"node_modules", ".venv", "__pycache__", "dist", ".git"}
    out = [p for p in PROJECT_ROOT.rglob("*.md")
           if not any(part in skip for part in p.parts)]
    return sorted(out)


@contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type:
        return
    except Exception as other:  # noqa: BLE001
        raise AssertionError(f"expected {exc_type.__name__}, got {type(other).__name__}: {other}")
    raise AssertionError(f"expected {exc_type.__name__}, but no exception was raised")


def _read(rel: str) -> str:
    path = PROJECT_ROOT / rel
    assert path.is_file(), f"missing required document: {rel}"
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------------
# Completeness — the artifacts M18 and D6 name
# --------------------------------------------------------------------------------------------------
def test_every_required_document_exists() -> None:
    missing = [d for d in REQUIRED_DOCS if not (PROJECT_ROOT / d).is_file()]
    assert not missing, f"missing documents: {missing}"


def test_milestone_row_artifacts_are_all_present() -> None:
    """The M18 row names eight artifacts by name; each must exist."""
    named = {
        "README": "README.md",
        "API docs": "docs/api/README.md",
        "architecture": "docs/planning/03_ARCHITECTURE.md",
        "dataset guide": "docs/datasets/README.md",
        "install": "docs/install/README.md",
        "user manual": "docs/user_guide/README.md",
        "dev guide": "docs/developer_guide/README.md",
        "deployment guide": "docs/deployment/README.md",
    }
    for label, rel in named.items():
        assert (PROJECT_ROOT / rel).is_file(), f"M18 names '{label}' but {rel} is missing"


def test_documentation_index_links_every_guide() -> None:
    index = _read("docs/README.md")
    for target in ("install/README.md", "user_guide/README.md", "developer_guide/README.md",
                   "api/README.md", "deployment/README.md", "MANIFEST.md",
                   "planning/10_DOCUMENTATION_AUDIT.md"):
        assert target in index, f"docs/README.md does not link {target}"


# --------------------------------------------------------------------------------------------------
# Consistency — links, ADRs, referenced paths
# --------------------------------------------------------------------------------------------------
_LINK = re.compile(r"\[[^\]]*\]\(([^)#][^)]*)\)")


def test_no_broken_relative_links_in_markdown() -> None:
    """Every relative Markdown link must resolve to a file that exists."""
    broken: list[str] = []
    for md in _all_markdown():
        for target in _LINK.findall(md.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#", "<")):
                continue
            resolved = (md.parent / target.split("#")[0]).resolve()
            if not resolved.exists():
                broken.append(f"{md.relative_to(PROJECT_ROOT)} -> {target}")
    assert not broken, "broken relative links:\n  " + "\n  ".join(broken)


def test_every_referenced_adr_file_exists() -> None:
    """A dangling ADR reference was a real defect M1 had to fix; keep it fixed."""
    referenced: set[str] = set()
    for md in _all_markdown():
        referenced.update(re.findall(r"ADR-\d{4}", md.read_text(encoding="utf-8")))
    on_disk = {p.name[:8] for p in (DOCS / "adr").glob("ADR-*.md")}
    # ADR-0005 was never issued. The docs say so explicitly, so naming it is a deliberate
    # statement about the numbering, not a dangling reference to a missing decision record.
    documented_unissued = {"ADR-0005"}
    dangling = sorted(referenced - on_disk - documented_unissued)
    assert dangling == [], f"referenced but non-existent ADRs: {dangling}"
    assert not (DOCS / "adr" / "ADR-0005.md").exists(), \
        "ADR-0005 now exists — remove it from the documented-unissued set"


def test_adr_numbering_has_no_unexpected_gaps() -> None:
    """ADRs run 0001..N with exactly one intentional gap (0005 was never issued)."""
    numbers = sorted(int(p.name[4:8]) for p in (DOCS / "adr").glob("ADR-*.md"))
    assert numbers[0] == 1, "ADR numbering must start at 0001"
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
    assert missing == [5], f"unexpected ADR gaps (only 0005 is intentionally unissued): {missing}"


def test_scripts_referenced_by_the_guides_exist() -> None:
    """A guide that tells a reader to run a missing script is worse than no guide."""
    guides = ["docs/install/README.md", "docs/user_guide/README.md",
              "docs/developer_guide/README.md", "docs/README.md", "docs/MANIFEST.md"]
    missing: list[str] = []
    for guide in guides:
        for rel in re.findall(r"backend/(?:scripts|tests)/[A-Za-z0-9_]+\.py", _read(guide)):
            if not (PROJECT_ROOT / rel).is_file():
                missing.append(f"{guide} -> {rel}")
    assert not missing, f"guides reference missing files: {missing}"


# --------------------------------------------------------------------------------------------------
# Staleness — the specific defects M18 found
# --------------------------------------------------------------------------------------------------
#: Quoted spans — a document may *quote* an old claim while explaining that it was wrong.
_QUOTED = re.compile(r"[\"\u201c\u201d][^\"\u201c\u201d\n]{0,200}[\"\u201c\u201d]")


def test_readmes_do_not_claim_the_project_is_a_scaffold() -> None:
    """Both READMEs described an M2 scaffold fifteen milestones after it stopped being one.

    Quoted text is excluded: the M18 section quotes the old wording to explain what was fixed, which
    is the opposite of reasserting it. Only an unquoted occurrence is a live stale claim.
    """
    for rel in ("README.md", "backend/README.md"):
        unquoted = _QUOTED.sub("", _read(rel))
        for stale in ("Milestone 2 (Project Scaffold) complete",
                      "Milestone 2 status: scaffold only",
                      "no application logic",
                      "nothing installed"):
            assert stale not in unquoted, f"{rel} still contains the stale M2 claim: {stale!r}"


def test_readme_reports_the_current_milestone() -> None:
    """Whatever milestone the plan says is latest-complete, the README must say the same.

    Derived from the plan rather than hard-coded, so this check keeps working each milestone instead
    of needing to be edited (and therefore silently weakened) every time.
    """
    plan = _read("docs/planning/07_MILESTONE_PLAN.md")
    completed = sorted(int(n) for n in re.findall(r"\*\*M(\d+): COMPLETE\*\*", plan))
    assert completed, "the milestone plan records no completed milestone"
    latest = completed[-1]
    readme = _read("README.md")
    assert f"Milestone {latest}" in readme or f"M{latest} " in readme, (
        f"the plan's latest completed milestone is M{latest}; the root README does not mention it")


def test_generated_api_reference_is_marked_generated() -> None:
    api = _read("docs/api/README.md")
    assert "GENERATED FILE" in api, "the generated API reference must say so"
    assert "generate_api_docs.py" in api, "it must name the generator"
    assert (PROJECT_ROOT / "backend/scripts/generate_api_docs.py").is_file()


def test_api_reference_covers_every_route_in_the_app() -> None:
    """The committed reference must not silently fall behind the routers."""
    from app.main import create_app
    schema = create_app().openapi()
    api_doc = _read("docs/api/README.md")
    missing = [p for p in schema["paths"] if f"`{p}`" not in api_doc]
    assert not missing, f"routes missing from docs/api/README.md (regenerate): {missing}"


# --------------------------------------------------------------------------------------------------
# Honesty — no document may promote an unmeasured result
# --------------------------------------------------------------------------------------------------
def test_kpis_are_still_reported_as_not_yet_measured() -> None:
    kpi = _read("docs/planning/06_KPI_ACCEPTANCE.md")
    assert "NOT YET MEASURED" in kpi, "the KPI table must still report NOT YET MEASURED"
    assert kpi.count("NOT YET MEASURED") >= 6, "every KPI row must still be unmeasured"


def test_m11_conclusion_is_still_mixed_everywhere_it_appears() -> None:
    report = _read("docs/comparison/real_experiment_cloudsen12.md")
    assert "MIXED" in report, "the M11 real-data conclusion must remain MIXED"
    for rel in ("docs/MANIFEST.md", "docs/user_guide/README.md", "docs/README.md"):
        text = _read(rel)
        if "M11" in text or "Attention U-Net" in text or "comparison" in text.lower():
            assert "MIXED" in text, f"{rel} discusses the comparison without stating MIXED"


def test_no_guide_claims_a_measured_kpi() -> None:
    """Catch a guide inventing a headline number for a KPI that was never measured."""
    forbidden = re.compile(r"KPI-(?:E?\d)\s*[:=]?\s*(?:is\s+)?\d+(?:\.\d+)?\s*%")
    for rel in ("docs/README.md", "docs/MANIFEST.md", "docs/install/README.md",
                "docs/user_guide/README.md", "docs/developer_guide/README.md",
                "docs/api/README.md"):
        hit = forbidden.search(_read(rel))
        assert hit is None, f"{rel} appears to state a measured KPI value: {hit.group(0)!r}"


def test_honesty_labels_are_defined_for_the_reader() -> None:
    """A label only helps if the reader is told what it means."""
    user = _read("docs/user_guide/README.md")
    for label in ("REAL", "SYNTHETIC", "DEMO", "DEFERRED", "NOT YET MEASURED"):
        assert label in user, f"the user manual must explain the {label} label"


def test_manifest_records_the_unbuilt_fr2_components() -> None:
    """FR-2 names a reference script and an oracle that were never implemented."""
    manifest = _read("docs/MANIFEST.md")
    assert "run_reference" in manifest and "oracle" in manifest, \
        "the manifest must record the unbuilt FR-2 components rather than implying they exist"
    assert not (PROJECT_ROOT / "backend/scripts/run_reference.sh").exists(), \
        "run_reference.sh now exists — update the manifest and the audit"
    assert not (PROJECT_ROOT / "backend/app/evaluation/oracle.py").exists(), \
        "oracle.py now exists — update the manifest and the audit"


# --------------------------------------------------------------------------------------------------
# M18 must not have changed the system
# --------------------------------------------------------------------------------------------------
def test_m18_did_not_weaken_the_negative_tests() -> None:
    from app.acceptance import run_acceptance
    report = run_acceptance()
    assert len(report.nt_results) == 5 and all(nt.passed for nt in report.nt_results)
    assert report.kpi_overall == "NOT_YET_MEASURED"


def test_docs_version_constant_is_registered() -> None:
    from app.core import constants as C
    assert C.DOCS_VERSION == "0.18.0"


def test_api_contract_is_unchanged_by_m18() -> None:
    from app.main import create_app
    paths = set(create_app().openapi()["paths"])
    expected = {"/version", "/health", "/metrics", "/models", "/models/register", "/train",
                "/predict", "/evaluate", "/history", "/upload", "/status",
                "/recover/{event_id}", "/lineage", "/pipeline", "/acceptance"}
    assert paths == expected, f"M18 changed the API surface: {paths ^ expected}"


# --------------------------------------------------------------------------------------------------
# Standalone manual harness (pytest is not installed in this project's venv)
# --------------------------------------------------------------------------------------------------
def _run_all() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
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
