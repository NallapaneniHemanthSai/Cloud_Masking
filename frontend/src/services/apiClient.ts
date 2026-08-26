// Centralized axios client + error normalization. Every API call in the app goes through here so base
// URL, timeouts, and error shape are consistent (ADR-0014). Config is environment-driven (VITE_*).
import axios, { AxiosError } from 'axios';

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
});

export interface ApiError {
  status?: number;
  detail: string;
  error_type: string;
}

// Normalize any thrown value into a consistent ApiError (surfacing the backend `detail` when present).
export function toApiError(err: unknown): ApiError {
  const ax = err as AxiosError<{ detail?: string; error_type?: string }>;
  if (ax && ax.isAxiosError) {
    const data = ax.response?.data;
    return {
      status: ax.response?.status,
      detail: data?.detail || ax.message || 'Request failed',
      error_type: data?.error_type || (ax.code ?? 'network_error'),
    };
  }
  return { detail: err instanceof Error ? err.message : String(err), error_type: 'error' };
}
