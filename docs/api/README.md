# API Reference — Cloud Masking API v0.13.0

> **GENERATED FILE — do not edit by hand.**
> Produced from the live OpenAPI schema by `backend/scripts/generate_api_docs.py`
> (ADR-0018). Regenerate after any router or DTO change:
>
> ```bash
> backend/.venv/bin/python backend/scripts/generate_api_docs.py
> ```

Backend API for multispectral Sentinel-2 cloud segmentation (M13).

## Conventions

- **Base URL.** Direct: `http://localhost:8000`. Through the frontend (dev *and* Docker):
  `http://localhost:8080/api` — the `/api` prefix is stripped before the request reaches the
  backend, so `/api/health` here is `/health` there (ADR-0014 / ADR-0017).
- **Content type.** JSON, except `POST /upload` (`multipart/form-data`).
- **Errors.** Domain failures return `{"detail": str, "error_type": str}` with **422**;
  a torch-only action attempted without PyTorch returns **503**; an unknown recovery event
  returns **404**. Validation errors use FastAPI's standard **422** body.
- **Authentication.** None. The API is unauthenticated by design and is intended for local /
  single-host operation only (ADR-0013 non-scope, ADR-0017 limitations).

> **Honesty:** every result this API produces from its default paths is
> **SYNTHETIC / VALIDATION ONLY** or **DEMO**. `POST /train` and `POST /evaluate` use bounded synthetic
> tensors and are **not** benchmarks; `POST /predict` on an untrained model returns a structural
> mask, not a measurement. No formal KPI is served by any endpoint — they remain **NOT YET
> MEASURED** — and the bounded M11 real-data conclusion remains **MIXED**.

## Endpoints

15 operations across 9 groups. Swagger UI is live at `/docs` and the raw schema at `/openapi.json`.

### `system`

Liveness, component versions and in-process telemetry (M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/health` | — | [`HealthResponse`](#healthresponse) |
| `GET` | `/metrics` | — | [`MetricsResponse`](#metricsresponse) |
| `GET` | `/version` | — | [`VersionResponse`](#versionresponse) |

### `models`

The model registry: available architectures and recorded model versions (M6/M10/M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/models` | — | [`ModelsResponse`](#modelsresponse) |
| `POST` | `/models/register` | free-form `object` | free-form `object` |

### `training`

Bounded **SYNTHETIC** training through the M7 trainer. Never a benchmark run (M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/train` | [`TrainRequest`](#trainrequest) | [`TrainResponse`](#trainresponse) |

### `prediction`

Inference through the M6 models + M4 preprocessing (M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/predict` | [`PredictRequest`](#predictrequest) | [`PredictResponse`](#predictresponse) |

### `evaluation`

Metrics through the M8 evaluation engine (M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/evaluate` | [`EvaluateRequest`](#evaluaterequest) | [`EvaluateResponse`](#evaluateresponse) |

### `history`

Persisted training runs, predictions, evaluations and uploads (M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/history` | `limit` | [`HistoryResponse`](#historyresponse) |

### `upload`

Raster upload into the git-ignored uploads directory, content-hashed (M13).

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/upload` | [`Body_upload_upload_post`](#body_upload_upload_post) | [`UploadResponse`](#uploadresponse) |

### `integration`

System status, degraded mode + recovery, NT-5 lineage, and the masking pipeline (M15).

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/lineage` | `limit` | [`LineageResponse`](#lineageresponse) |
| `POST` | `/pipeline` | [`PipelineRequest`](#pipelinerequest) | [`PipelineResponse`](#pipelineresponse) |
| `POST` | `/recover/{event_id}` | `event_id`, `note` | [`RecoverResponse`](#recoverresponse) |
| `GET` | `/status` | — | [`StatusResponse`](#statusresponse) |

### `acceptance`

The D5 acceptance harness verdict — NT-1..NT-5 on SYNTHETIC fixtures (M16).

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/acceptance` | — | [`AcceptanceResponse`](#acceptanceresponse) |

## Data models

23 Pydantic v2 DTOs (`backend/app/schemas/api.py`). Fields marked **required** must be supplied.

### `AcceptanceResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `acceptance_version` | `string` | yes | — |
| `overall` | `string` | yes | — |
| `safety_passed` | `boolean` | yes | — |
| `kpi_overall` | `string` | yes | — |
| `failed_nts` | array<`string`> | no | — |
| `nt_results` | array<object<any>> | no | — |
| `ac_coverage` | array<object<any>> | no | — |
| `kpi_status` | array<object<any>> | no | — |
| `coverage` | object<any> | no | — |
| `content_hash` | `string` | no | `` |
| `notes` | `string` | no | `` |

### `Body_upload_upload_post`

| Field | Type | Required | Default |
|---|---|---|---|
| `file` | `string` | yes | — |

### `EvaluateRequest`

| Field | Type | Required | Default |
|---|---|---|---|
| `mode` | `string` | no | `multiclass` |
| `dataset` | `string` | no | `cloudsen12` |
| `split` | `string` | no | `test` |
| `seed` | `integer` | no | `0` |
| `synthetic` | `boolean` | no | `True` |

### `EvaluateResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `evaluation_id` | `string` | yes | — |
| `dataset` | `string` | yes | — |
| `split` | `string` | yes | — |
| `data_regime` | `string` | yes | — |
| `pixel_accuracy` | `number` \| `null` | no | — |
| `macro_iou` | `number` \| `null` | no | — |
| `thin_cloud_iou` | `number` \| `null` | no | — |
| `per_class_iou` | object<`number` \| `null`> | no | — |
| `config_hash` | `string` | no | `` |
| `notes` | `string` | no | `` |

### `HTTPValidationError`

| Field | Type | Required | Default |
|---|---|---|---|
| `detail` | array<[`ValidationError`](#validationerror)> | no | — |

### `HealthResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `status` | `string` | no | `ok` |
| `torch_available` | `boolean` | yes | — |
| `device` | `string` | yes | — |
| `database` | `string` | yes | — |

### `HistoryResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `training_runs` | array<object<any>> | no | — |
| `predictions` | array<object<any>> | no | — |
| `evaluations` | array<object<any>> | no | — |
| `uploads` | array<object<any>> | no | — |

### `LineageResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `nodes` | array<object<any>> | no | — |

### `MetricsResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `uptime_seconds` | `number` | yes | — |
| `total_requests` | `integer` | yes | — |
| `total_errors` | `integer` | yes | — |
| `routes` | array<[`RouteMetric`](#routemetric)> | no | — |

### `ModelInfo`

| Field | Type | Required | Default |
|---|---|---|---|
| `architecture` | `string` | yes | — |
| `version` | `string` | yes | — |
| `description` | `string` | no | `` |
| `aliases` | array<`string`> | no | — |
| `improves_over` | `string` | no | `` |
| `supported_input_channels` | array<`integer`> | no | — |
| `supported_output_classes` | array<`integer`> | no | — |

### `ModelsResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `architectures` | array<[`ModelInfo`](#modelinfo)> | no | — |
| `registered_versions` | array<object<any>> | no | — |

### `PipelineRequest`

| Field | Type | Required | Default |
|---|---|---|---|
| `seed` | `integer` | no | `0` |
| `with_prediction` | `boolean` | no | `True` |
| `inject_guardrail_failure` | `boolean` | no | `False` |

### `PipelineResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `data_regime` | `string` | yes | — |
| `guardrail_passed` | `boolean` | yes | — |
| `guardrail_reasons` | array<`string`> | no | — |
| `degraded_event` | object<any> \| `null` | no | — |
| `status` | [`StatusResponse`](#statusresponse) | yes | — |
| `lineage` | array<object<any>> | no | — |
| `evaluation` | object<any> | no | — |
| `prediction` | object<any> \| `null` | no | — |
| `note` | `string` | no | `` |

### `PredictRequest`

| Field | Type | Required | Default |
|---|---|---|---|
| `architecture` | `string` | no | `unet` |
| `in_channels` | `integer` | no | `13` |
| `num_classes` | `integer` | no | `4` |
| `encoder_depth` | `integer` | no | `2` |
| `base_channels` | `integer` | no | `8` |
| `device` | `string` | no | `cpu` |
| `patch_size` | `integer` | no | `32` |
| `checkpoint_path` | `string` \| `null` | no | — |
| `image` | array<array<array<`number`>>> \| `null` | no | — |
| `synthetic` | `boolean` | no | `True` |

### `PredictResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `prediction_id` | `string` | yes | — |
| `architecture` | `string` | yes | — |
| `num_classes` | `integer` | yes | — |
| `input_shape` | array<`integer`> | yes | — |
| `output_shape` | array<`integer`> | yes | — |
| `device` | `string` | yes | — |
| `data_regime` | `string` | yes | — |
| `class_pixel_counts` | object<`integer`> | no | — |
| `source` | `string` | no | `` |
| `notes` | `string` | no | `` |

### `RecoverResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `event_id` | `string` | yes | — |
| `kind` | `string` | yes | — |
| `subject` | `string` | yes | — |
| `reason` | `string` | yes | — |
| `resolved` | `boolean` | yes | — |
| `resolves_event_id` | `string` \| `null` | no | — |
| `created_at` | `string` \| `null` | no | — |

### `RouteMetric`

| Field | Type | Required | Default |
|---|---|---|---|
| `route` | `string` | yes | — |
| `count` | `integer` | yes | — |
| `error_count` | `integer` | yes | — |
| `total_seconds` | `number` | yes | — |
| `avg_seconds` | `number` | yes | — |
| `last_seconds` | `number` | yes | — |

### `StatusResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `status` | `string` | yes | — |
| `degraded` | `boolean` | yes | — |
| `active_degraded_events` | array<object<any>> | no | — |
| `event_count` | `integer` | no | `0` |
| `lineage_count` | `integer` | no | `0` |

### `TrainRequest`

| Field | Type | Required | Default |
|---|---|---|---|
| `architecture` | `string` | no | `unet` |
| `in_channels` | `integer` | no | `13` |
| `num_classes` | `integer` | no | `4` |
| `encoder_depth` | `integer` | no | `2` |
| `base_channels` | `integer` | no | `8` |
| `epochs` | `integer` | no | `1` |
| `batch_size` | `integer` | no | `2` |
| `seed` | `integer` | no | `42` |
| `device` | `string` | no | `cpu` |
| `synthetic` | `boolean` | no | `True` |
| `synthetic_patch` | `integer` | no | `16` |
| `synthetic_batches` | `integer` | no | `2` |

### `TrainResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `run_id` | `string` | yes | — |
| `architecture` | `string` | yes | — |
| `status` | `string` | yes | — |
| `data_regime` | `string` | yes | — |
| `device` | `string` | yes | — |
| `epochs` | `integer` | yes | — |
| `duration_seconds` | `number` \| `null` | no | — |
| `best_metric` | `number` \| `null` | no | — |
| `final_loss` | `number` \| `null` | no | — |
| `training_config_hash` | `string` | yes | — |
| `parameter_count` | `integer` \| `null` | no | — |
| `notes` | `string` | no | `` |

### `UploadResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `upload_id` | `string` | yes | — |
| `filename` | `string` | yes | — |
| `content_hash` | `string` | yes | — |
| `size_bytes` | `integer` | yes | — |
| `content_type` | `string` | no | `` |
| `path` | `string` | no | `` |

### `ValidationError`

| Field | Type | Required | Default |
|---|---|---|---|
| `loc` | array<`string` \| `integer`> | yes | — |
| `msg` | `string` | yes | — |
| `type` | `string` | yes | — |

### `VersionResponse`

| Field | Type | Required | Default |
|---|---|---|---|
| `app_version` | `string` | yes | — |
| `model_version` | `string` | yes | — |
| `improved_model_version` | `string` | yes | — |
| `preprocessing_version` | `string` | yes | — |
| `visualization_version` | `string` | yes | — |
| `training_version` | `string` | yes | — |
| `evaluation_version` | `string` | yes | — |
| `failure_analysis_version` | `string` | yes | — |
| `comparison_version` | `string` | yes | — |
| `dataset_manifest_version` | `string` | yes | — |
| `python` | `string` | yes | — |
| `torch` | `string` \| `null` | no | — |

## Related documentation

- [User guide](../user_guide/README.md) — what these endpoints do for a person using the app.
- [Developer guide](../developer_guide/README.md) — how a router reaches the M6–M16 services.
- [Deployment guide](../deployment/README.md) — running the API in Docker.
- [ADR-0013](../adr/ADR-0013-backend-api.md) — why the API is shaped this way.
