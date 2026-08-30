"""Milestone 19 verification: research-paper evidence integrity.

Runs under pytest AND standalone (``python backend/tests/test_paper.py``). Framework-free.

A research write-up is where evidence labels are most likely to be quietly dropped, because prose
rewards confident, uniform claims. These checks enforce the ADR-0019 evidence policy mechanically:

* every ``\\cite`` key used in the paper resolves to an entry in ``references.bib``;
* every transcribed M11 number matches the M11 source record **exactly** (no drift, no rounding);
* the MIXED conclusion is preserved and the forbidden over-claim never appears;
* every ablation is labelled NOT EXECUTED;
* unmeasured KPIs are never presented as measured;
* the FR-2 gap is reported and the components genuinely do not exist.

No network, no real data, no new measurement.
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
PAPER = PROJECT_ROOT / "paper"
M11_SOURCE = PROJECT_ROOT / "docs" / "comparison" / "real_experiment_cloudsen12.md"

PAPER_DOCS = [
    "paper/README.md",
    "paper/00_RESEARCH_PAPER.md",
    "paper/01_LITERATURE_REVIEW.md",
    "paper/02_COMPARISON_TABLE.md",
    "paper/03_ABLATION_TEMPLATE.md",
    "paper/04_RESULTS.md",
    "paper/references.bib",
]


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
    p = PROJECT_ROOT / rel
    assert p.is_file(), f"missing M19 deliverable: {rel}"
    return p.read_text(encoding="utf-8")


def _paper_prose() -> str:
    """All paper prose (excluding the .bib), lowercased."""
    return "\n".join(_read(d) for d in PAPER_DOCS if not d.endswith(".bib")).lower()


# --------------------------------------------------------------------------------------------------
# Deliverables exist
# --------------------------------------------------------------------------------------------------
def test_all_m19_deliverables_exist() -> None:
    missing = [d for d in PAPER_DOCS if not (PROJECT_ROOT / d).is_file()]
    assert not missing, f"missing M19 deliverables: {missing}"


def test_milestone_named_artifacts_present() -> None:
    """The M19 row names five artifacts; each must have a document."""
    named = {
        "literature review": "paper/01_LITERATURE_REVIEW.md",
        "citations/references": "paper/references.bib",
        "comparison table": "paper/02_COMPARISON_TABLE.md",
        "ablation template": "paper/03_ABLATION_TEMPLATE.md",
        "results write-up": "paper/04_RESULTS.md",
    }
    for label, rel in named.items():
        assert (PROJECT_ROOT / rel).is_file(), f"M19 names '{label}' but {rel} is missing"


# --------------------------------------------------------------------------------------------------
# Citation integrity
# --------------------------------------------------------------------------------------------------
def _bib_keys() -> set[str]:
    return set(re.findall(r"@\w+\{([^,]+),", _read("paper/references.bib")))


def test_bibliography_has_entries() -> None:
    assert len(_bib_keys()) >= 10, "expected a substantive bibliography"


def test_every_cited_key_resolves_to_the_bibliography() -> None:
    """A citation key with no entry is an unverifiable claim."""
    keys = _bib_keys()
    used: set[str] = set()
    for doc in PAPER_DOCS:
        if doc.endswith(".bib"):
            continue
        used.update(re.findall(r"\[([a-z]+\d{4}[a-z0-9]*)\]", _read(doc)))
    dangling = sorted(used - keys)
    assert not dangling, f"citation keys with no bibliography entry: {dangling}"


def test_every_bibliography_entry_has_a_resolvable_identifier() -> None:
    """Each entry must carry a DOI or an arXiv eprint so a reviewer can verify it."""
    bib = _read("paper/references.bib")
    entries = re.split(r"\n@", bib)[1:]
    for e in entries:
        key = e.split("{", 1)[1].split(",", 1)[0]
        assert ("doi" in e.lower()) or ("eprint" in e.lower()), \
            f"bibliography entry {key!r} has neither a DOI nor an arXiv eprint"


def test_bibliography_entries_are_actually_used() -> None:
    prose = "\n".join(_read(d) for d in PAPER_DOCS if not d.endswith(".bib"))
    unused = sorted(k for k in _bib_keys() if k not in prose)
    assert not unused, f"bibliography entries never cited: {unused}"


# --------------------------------------------------------------------------------------------------
# Result provenance — transcription must match the M11 source exactly
# --------------------------------------------------------------------------------------------------
#: (label, literal) pairs that must appear in BOTH the M11 source record and the paper's results.
M11_FACTS = [
    ("thin-cloud mean delta", "+0.050"),
    ("thin seed 1 delta", "+0.047"),
    ("thin seed 2 delta", "+0.076"),
    ("thin seed 3 delta", "+0.028"),
    ("shadow seed 1 delta", "−0.003"),
    ("shadow seed 2 delta", "−0.029"),
    ("shadow seed 3 delta", "−0.022"),
    ("baseline params", "484,228"),
    ("improved params", "490,005"),
    ("thin seed 1 iou", "0.4605"),
    ("thin seed 2 iou", "0.4402"),
    ("thin seed 3 iou", "0.5244"),
    ("thin seed 1 fn", "115,948"),
    ("subset size", "32"),
    ("split", "train 22 / val 5 / test 5"),
    ("dataset version", "cloudsen12plus-1.1.2-l1c-p0-9045d5c3"),
]


def test_transcribed_numbers_match_the_m11_source_record() -> None:
    """Every figure quoted in the paper must exist verbatim in the M11 record."""
    source = M11_SOURCE.read_text(encoding="utf-8")
    results = _read("paper/04_RESULTS.md")
    for label, literal in M11_FACTS:
        assert literal in source, f"{label} {literal!r} is not in the M11 source record"
        assert literal in results, f"{label} {literal!r} was not transcribed into paper/04_RESULTS.md"


#: The document set uses a typographic minus (U+2212), not ASCII hyphen, in its tables.
MINUS = "\u2212"

#: Means the paper derives itself. Presence in the source is not required, but the arithmetic is
#: checked against the source's per-seed values, so a drifted or invented mean fails.
DERIVED_MEANS = {
    "clear":        ([-0.024, -0.014, +0.039], "+0.000"),
    "thick_cloud":  ([-0.057, +0.028, +0.122], "+0.031"),
    "thin_cloud":   ([+0.047, +0.076, +0.028], "+0.050"),
    "cloud_shadow": ([-0.003, -0.029, -0.022], "-0.018"),
    "macro":        ([-0.009, +0.015, +0.042], "+0.016"),
}


def test_every_number_in_the_results_is_sourced_or_correctly_derived() -> None:
    """Provenance, not just presence.

    A presence check is too weak: a drifted value can slip through while the correct literal still
    appears elsewhere on the page. So every signed decimal in the results write-up must either appear
    verbatim in the M11 record, or be a mean this page derives — and each derived mean is recomputed
    from the source's own per-seed values.
    """
    source = M11_SOURCE.read_text(encoding="utf-8")
    results = _read("paper/04_RESULTS.md")

    # 1. Each derived mean is arithmetically correct (and its per-seed inputs are in the source).
    for cls, (per_seed, stated) in DERIVED_MEANS.items():
        for v in per_seed:
            sign = "+" if v >= 0 else MINUS
            literal = sign + f"{abs(v):.3f}"
            assert literal in source, f"{cls}: per-seed value {literal} not in the M11 source"
        computed = sum(per_seed) / len(per_seed)
        assert abs(computed - float(stated)) < 5e-4, (
            f"{cls}: stated mean {stated} != arithmetic mean {computed:+.4f} of {per_seed}")
        shown = stated.replace("-", MINUS)
        assert shown in results, f"{cls}: derived mean {shown} missing from the results write-up"

    # 2. No signed decimal may appear that is neither in the source nor a verified derived mean.
    allowed = set(re.findall(r"[+\u2212-]\d\.\d{3}", source))
    allowed |= {s.replace("-", MINUS) for _, s in DERIVED_MEANS.values()}
    allowed |= {"+0.079", "+0.149", "+0.111"}   # recall deltas, arithmetic from source recall pairs
    unsourced = sorted({m for m in re.findall(r"[+\u2212]\d\.\d{3}", results)} - allowed)
    assert not unsourced, f"values in the paper with no M11 provenance: {unsourced}"


def test_recall_deltas_are_arithmetically_correct() -> None:
    """The recall improvements the paper states must follow from the source's recall pairs."""
    pairs = [(0.666, 0.745, "+0.079"), (0.556, 0.705, "+0.149"), (0.736, 0.847, "+0.111")]
    source = M11_SOURCE.read_text(encoding="utf-8")
    for base, impr, stated in pairs:
        arrow = "\u2192"
        assert f"{base:.3f} {arrow} {impr:.3f}" in source, \
            f"recall pair {base}->{impr} not found in the M11 source"
        assert abs((impr - base) - float(stated)) < 5e-4, \
            f"stated recall delta {stated} != {impr - base:+.4f}"


def test_parameter_counts_match_the_model_code() -> None:
    """Independently re-derive the quoted parameter counts from the models themselves."""
    from app.models.config import ModelConfig
    from app.models.factory import ModelFactory
    factory = ModelFactory()
    counts = {}
    for arch in ("unet", "attention_unet"):
        model = factory.create(ModelConfig(name=arch, in_channels=13, num_classes=4,
                                           encoder_depth=3, base_channels=16))
        counts[arch] = sum(p.numel() for p in model.parameters())
    assert counts["unet"] == 484228, f"baseline params drifted: {counts['unet']}"
    assert counts["attention_unet"] == 490005, f"improved params drifted: {counts['attention_unet']}"


def test_no_invented_statistical_claims() -> None:
    """n=3 supports consistency, not significance (ADR-0011 / ADR-0019 §6)."""
    prose = _paper_prose()
    for forbidden in ("p < 0.05", "p<0.05", "p-value", "statistically significant",
                      "confidence interval of", "95% ci"):
        assert forbidden not in prose, f"unsupported statistical claim in the paper: {forbidden!r}"


# --------------------------------------------------------------------------------------------------
# The MIXED conclusion
# --------------------------------------------------------------------------------------------------
def test_mixed_conclusion_is_stated_in_every_summary_document() -> None:
    for doc in ("paper/README.md", "paper/00_RESEARCH_PAPER.md",
                "paper/02_COMPARISON_TABLE.md", "paper/04_RESULTS.md"):
        assert "MIXED" in _read(doc), f"{doc} does not state the MIXED conclusion"


def test_the_forbidden_overclaim_never_appears_as_an_assertion() -> None:
    """"Attention U-Net is better" is exactly the compression ADR-0019 exists to prevent.

    Quoted/negated mentions (the paper explicitly forbids the phrase) are excluded; only an
    unquoted assertion is a violation.
    """
    quoted = re.compile(r"[\"“”][^\"“”\n]{0,300}[\"“”]")
    for doc in PAPER_DOCS:
        if doc.endswith(".bib"):
            continue
        text = quoted.sub("", _read(doc)).lower()
        for claim in ("attention u-net is better", "attention u-net outperforms",
                      "attention u-net is superior"):
            assert claim not in text, f"{doc} makes the unsupported claim: {claim!r}"


def test_cloud_shadow_regression_is_reported_wherever_the_gain_is() -> None:
    """Reporting the thin-cloud gain without the shadow regression is selective reporting."""
    for doc in ("paper/00_RESEARCH_PAPER.md", "paper/02_COMPARISON_TABLE.md",
                "paper/04_RESULTS.md", "paper/README.md"):
        text = _read(doc)
        if "+0.050" in text:
            assert "−0.018" in text or "cloud_shadow" in text or "cloud-shadow" in text, \
                f"{doc} reports the thin-cloud gain without the cloud-shadow regression"


def test_seed_dependence_of_the_verdict_is_disclosed() -> None:
    paper = _read("paper/00_RESEARCH_PAPER.md")
    assert "IMPROVED" in paper and "REGRESSION" in paper, \
        "the paper must disclose that the framework verdict flips across seeds"


# --------------------------------------------------------------------------------------------------
# Unexecuted work must be labelled
# --------------------------------------------------------------------------------------------------
def test_every_ablation_is_labelled_not_executed() -> None:
    abl = _read("paper/03_ABLATION_TEMPLATE.md")
    assert abl.count("NOT EXECUTED") >= 7, "each specified ablation must be labelled NOT EXECUTED"
    assert "NOT EXECUTED" in abl.split("## Priority")[0]


def test_kpis_are_not_presented_as_measured() -> None:
    prose = "\n".join(_read(d) for d in PAPER_DOCS if not d.endswith(".bib"))
    assert "NOT YET MEASURED" in prose, "the paper must state that the formal KPIs are unmeasured"
    # A KPI id followed by a numeric value would be a fabricated measurement.
    hit = re.search(r"KPI-(?:E?\d)\s*[:=]?\s*(?:is\s+)?\d+(?:\.\d+)?\s*%", prose)
    assert hit is None, f"paper appears to state a measured KPI value: {hit.group(0) if hit else ''!r}"
    kpi_doc = _read("docs/planning/06_KPI_ACCEPTANCE.md")
    assert kpi_doc.count("NOT YET MEASURED") >= 6, "the KPI table itself must stay unmeasured"


def test_synthetic_evidence_is_never_labelled_real() -> None:
    results = _read("paper/04_RESULTS.md")
    assert "SYNTHETIC" in results, "the results page must keep the synthetic class distinct"
    assert "REAL — BOUNDED M11 EXPERIMENT" in results, \
        "real evidence must carry the bounded-experiment label, not a bare REAL"


# --------------------------------------------------------------------------------------------------
# FR-2 reproducibility gap
# --------------------------------------------------------------------------------------------------
def test_fr2_gap_is_reported_and_the_components_really_are_absent() -> None:
    paper = _read("paper/00_RESEARCH_PAPER.md")
    assert "run_reference.sh" in paper and "oracle.py" in paper, \
        "the paper must report the FR-2 reproducibility gap"
    assert "NOT BUILT" in paper
    # If someone builds them, this test must fail so the paper gets updated.
    assert not (PROJECT_ROOT / "backend/scripts/run_reference.sh").exists(), \
        "run_reference.sh now exists — update the paper's reproducibility section"
    assert not (PROJECT_ROOT / "backend/app/evaluation/oracle.py").exists(), \
        "oracle.py now exists — update the paper's reproducibility section"


# --------------------------------------------------------------------------------------------------
# M19 changed nothing in the system
# --------------------------------------------------------------------------------------------------
def test_m19_did_not_weaken_the_negative_tests() -> None:
    from app.acceptance import run_acceptance
    report = run_acceptance()
    assert len(report.nt_results) == 5 and all(nt.passed for nt in report.nt_results)
    assert report.kpi_overall == "NOT_YET_MEASURED"


def test_paper_version_constant_is_registered() -> None:
    from app.core import constants as C
    assert C.PAPER_VERSION == "0.19.0"


def test_no_broken_relative_links_in_the_paper() -> None:
    link = re.compile(r"\[[^\]]*\]\(([^)#][^)]*)\)")
    broken: list[str] = []
    for doc in PAPER_DOCS:
        if doc.endswith(".bib"):
            continue
        path = PROJECT_ROOT / doc
        for target in link.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not (path.parent / target.split("#")[0]).resolve().exists():
                broken.append(f"{doc} -> {target}")
    assert not broken, f"broken links in the paper: {broken}"


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
