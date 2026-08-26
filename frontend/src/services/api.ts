// One typed function per M13 endpoint. No domain logic — pure HTTP mapping (ADR-0014).
import { apiClient } from './apiClient';
import type {
  EvaluateRequest,
  EvaluateResponse,
  HealthResponse,
  HistoryResponse,
  MetricsResponse,
  ModelsResponse,
  PredictRequest,
  PredictResponse,
  TrainRequest,
  TrainResponse,
  UploadResponse,
  VersionResponse,
} from './types';

export const getVersion = () =>
  apiClient.get<VersionResponse>('/version').then((r) => r.data);

export const getHealth = () =>
  apiClient.get<HealthResponse>('/health').then((r) => r.data);

export const getMetrics = () =>
  apiClient.get<MetricsResponse>('/metrics').then((r) => r.data);

export const getModels = () =>
  apiClient.get<ModelsResponse>('/models').then((r) => r.data);

export const getHistory = (limit = 50) =>
  apiClient.get<HistoryResponse>('/history', { params: { limit } }).then((r) => r.data);

export const postTrain = (body: Partial<TrainRequest>) =>
  apiClient.post<TrainResponse>('/train', body).then((r) => r.data);

export const postPredict = (body: Partial<PredictRequest>) =>
  apiClient.post<PredictResponse>('/predict', body).then((r) => r.data);

export const postEvaluate = (body: Partial<EvaluateRequest>) =>
  apiClient.post<EvaluateResponse>('/evaluate', body).then((r) => r.data);

export const postUpload = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return apiClient
    .post<UploadResponse>('/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((r) => r.data);
};
