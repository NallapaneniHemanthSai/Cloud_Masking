// TypeScript interfaces mirroring the M13 backend Pydantic DTOs (app/schemas/api.py).
// These are the single source of API-shape truth for the frontend; keep in sync with the backend.

export interface VersionResponse {
  app_version: string;
  model_version: string;
  improved_model_version: string;
  preprocessing_version: string;
  visualization_version: string;
  training_version: string;
  evaluation_version: string;
  failure_analysis_version: string;
  comparison_version: string;
  dataset_manifest_version: string;
  python: string;
  torch: string | null;
}

export interface HealthResponse {
  status: string;
  torch_available: boolean;
  device: string;
  database: string;
}

export interface RouteMetric {
  route: string;
  count: number;
  error_count: number;
  total_seconds: number;
  avg_seconds: number;
  last_seconds: number;
}

export interface MetricsResponse {
  uptime_seconds: number;
  total_requests: number;
  total_errors: number;
  routes: RouteMetric[];
}

export interface ModelInfo {
  architecture: string;
  version: string;
  description: string;
  aliases: string[];
  improves_over: string;
  supported_input_channels: number[];
  supported_output_classes: number[];
}

export interface RegisteredVersion {
  id: number;
  model_id: string;
  architecture: string;
  version: string;
  config_hash: string;
  parameter_count: number | null;
  notes: string;
  created_at: string | null;
}

export interface ModelsResponse {
  architectures: ModelInfo[];
  registered_versions: RegisteredVersion[];
}

export interface TrainRequest {
  architecture: string;
  in_channels: number;
  num_classes: number;
  encoder_depth: number;
  base_channels: number;
  epochs: number;
  batch_size: number;
  seed: number;
  device: string;
  synthetic: boolean;
  synthetic_patch: number;
  synthetic_batches: number;
}

export interface TrainResponse {
  run_id: string;
  architecture: string;
  status: string;
  data_regime: string;
  device: string;
  epochs: number;
  duration_seconds: number | null;
  best_metric: number | null;
  final_loss: number | null;
  training_config_hash: string;
  parameter_count: number | null;
  notes: string;
}

export interface PredictRequest {
  architecture: string;
  in_channels: number;
  num_classes: number;
  encoder_depth: number;
  base_channels: number;
  device: string;
  patch_size: number;
  checkpoint_path: string | null;
  image: number[][][] | null;
  synthetic: boolean;
}

export interface PredictResponse {
  prediction_id: string;
  architecture: string;
  num_classes: number;
  input_shape: number[];
  output_shape: number[];
  device: string;
  data_regime: string;
  class_pixel_counts: Record<string, number>;
  source: string;
  notes: string;
}

export interface EvaluateRequest {
  mode: string;
  dataset: string;
  split: string;
  seed: number;
  synthetic: boolean;
}

export interface EvaluateResponse {
  evaluation_id: string;
  dataset: string;
  split: string;
  data_regime: string;
  pixel_accuracy: number | null;
  macro_iou: number | null;
  thin_cloud_iou: number | null;
  per_class_iou: Record<string, number | null>;
  config_hash: string;
  notes: string;
}

export interface UploadResponse {
  upload_id: string;
  filename: string;
  content_hash: string;
  size_bytes: number;
  content_type: string;
  path: string;
}

export interface HistoryResponse {
  training_runs: Record<string, unknown>[];
  predictions: Record<string, unknown>[];
  evaluations: Record<string, unknown>[];
  uploads: Record<string, unknown>[];
}
