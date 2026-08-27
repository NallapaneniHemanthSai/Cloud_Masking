# Documentation Index

Everything written about the Cloud Masking system. Start with the row that matches why you are here.

| I want to… | Read |
|------------|------|
| **Get it running** | [Installation guide](install/README.md) |
| **Use it** | [User manual](user_guide/README.md) |
| **Change the code** | [Developer guide](developer_guide/README.md) |
| **Call the API** | [API reference](api/README.md) *(generated)* |
| **Deploy it** | [Deployment guide](deployment/README.md) |
| **Review it** *(O5)* | [Package manifest](MANIFEST.md) → [Acceptance harness](acceptance/README.md) → [KPIs & negative tests](planning/06_KPI_ACCEPTANCE.md) |
| **Know what was actually measured** | [Real experiment report](comparison/real_experiment_cloudsen12.md) |

> **Before citing any number from this project:** exactly one result is REAL — the bounded
> CloudSEN12+ comparison, whose conclusion is **MIXED**. Every formal KPI is **NOT YET MEASURED**.
> Everything else is SYNTHETIC or DEMO and is labelled as such at the point of display.

---

## Guides

| Document | Covers |
|----------|--------|
| [Installation](install/README.md) | Docker path, host path, configuration, troubleshooting |
| [User manual](user_guide/README.md) | Every UI page, the honesty labels, typical flows |
| [Developer guide](developer_guide/README.md) | Architecture, conventions, tests, extension points, reproducibility |
| [API reference](api/README.md) | 15 endpoints, 23 DTOs — generated from OpenAPI |
| [Deployment](deployment/README.md) | Images, compose, volumes, health checks, restart behaviour |
| [Package manifest](MANIFEST.md) | Inventory, provenance, licences, evidence status |

## Planning & acceptance (D1)

| Document | Covers |
|----------|--------|
| [00 Project charter](planning/00_PROJECT_CHARTER.md) | Problem, objectives, stakeholders |
| [01 Requirements](planning/01_REQUIREMENTS.md) | FR/NFR + full traceability matrix |
| [02 System boundary](planning/02_SYSTEM_BOUNDARY.md) | In scope vs out of scope |
| [03 Architecture](planning/03_ARCHITECTURE.md) | Clean-architecture layout, component diagram |
| [04 Source-to-claim map](planning/04_SOURCE_TO_CLAIM_MAP.md) | Every claim → its evidence |
| [05 Risk register](planning/05_RISK_REGISTER.md) | R-01..R-17 with mitigations |
| [06 KPIs & acceptance](planning/06_KPI_ACCEPTANCE.md) | KPI-1..6, KPI-E1..E7, AC-1..4, **NT-1..NT-5** |
| [07 Milestone plan](planning/07_MILESTONE_PLAN.md) | 20 milestones, gates, current status |
| [08 Assumptions](planning/08_ASSUMPTIONS.md) | Open assumptions with owners |
| [09 Consistency audit](planning/09_CONSISTENCY_AUDIT.md) | M1 cross-document audit |
| [10 Documentation audit](planning/10_DOCUMENTATION_AUDIT.md) | **M18** completeness & consistency audit |

## Per-milestone references

| Area | Document |
|------|----------|
| Datasets | [datasets/](datasets/README.md) · [CloudSEN12](datasets/cloudsen12.md) · [On Cloud N](datasets/on_cloud_n.md) · [licences](datasets/licenses.md) · [experimental pipeline](datasets/experimental_pipeline.md) |
| Preprocessing | [preprocessing/](preprocessing/README.md) |
| Visualization | [visualization/](visualization/README.md) |
| Models | [models/](models/README.md) · [improved model](models/improved_model.md) |
| Training | [training/](training/README.md) |
| Evaluation | [evaluation/](evaluation/README.md) |
| Failure analysis | [failure_analysis/](failure_analysis/README.md) |
| Comparison | [comparison/](comparison/README.md) · [**real experiment**](comparison/real_experiment_cloudsen12.md) |
| Integration | [integration/](integration/README.md) |
| Acceptance (D5) | [acceptance/](acceptance/README.md) |
| Deployment | [deployment/](deployment/README.md) |

## Decision records

Numbered, dated, and stating what was **rejected** as well as chosen. ADR-0005 was never issued.

| ADR | Decision |
|-----|----------|
| [0001](adr/ADR-0001-dataset-selection.md) | CloudSEN12 primary + On Cloud N reference |
| [0002](adr/ADR-0002-compute-environment.md) | Mac MPS/CPU, config-driven device detection |
| [0003](adr/ADR-0003-change-detection-source.md) | Change-detection source *(deferred)* |
| [0004](adr/ADR-0004-python-runtime.md) | Pin Python 3.11.x |
| [0006](adr/ADR-0006-baseline-model-selection.md) | U-Net baseline |
| [0007](adr/ADR-0007-training-strategy.md) | Config-driven trainer |
| [0008](adr/ADR-0008-evaluation-strategy.md) | Confusion-first, stratified metrics |
| [0009](adr/ADR-0009-confusing-case-analysis.md) | Failure taxonomy |
| [0010](adr/ADR-0010-improved-model-selection.md) | Attention U-Net |
| [0011](adr/ADR-0011-model-comparison.md) | Fair comparison + decision framework |
| [0012](adr/ADR-0012-experimental-dataset-and-data-pipeline.md) | Dataset readiness gate |
| [0013](adr/ADR-0013-backend-api.md) | FastAPI + SQLite + telemetry |
| [0014](adr/ADR-0014-frontend.md) | React SPA + same-origin `/api` proxy |
| [0015](adr/ADR-0015-integration-degraded-recovery.md) | Degraded mode, recovery, NT-5 |
| [0016](adr/ADR-0016-acceptance-harness.md) | D5 acceptance harness |
| [0017](adr/ADR-0017-deployment-containerization.md) | Docker + Compose |
| [0018](adr/ADR-0018-documentation-and-release-packaging.md) | Documentation & release packaging |

---

## Keeping these documents honest

"Docs complete & consistent" is M18's exit criterion, so it is **executable** rather than asserted:

```bash
backend/.venv/bin/python backend/tests/test_documentation.py          # required docs, links, labels
backend/.venv/bin/python backend/scripts/generate_api_docs.py --check # API reference not stale
```

The API reference is generated from the OpenAPI schema — edit the code, then regenerate; never edit
`api/README.md` by hand.
