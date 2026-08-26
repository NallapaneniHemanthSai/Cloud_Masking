// Caches /version + /health once for the whole app (header + Dashboard), avoiding refetch per page.
import { createContext, useContext, type ReactNode } from 'react';
import { getHealth, getVersion } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import type { HealthResponse, VersionResponse } from '../services/types';
import type { ApiError } from '../services/apiClient';

interface SystemState {
  version?: VersionResponse;
  health?: HealthResponse;
  loading: boolean;
  error?: ApiError;
  reload: () => void;
}

const SystemCtx = createContext<SystemState | null>(null);

export function SystemProvider({ children }: { children: ReactNode }) {
  const version = useApiResource<VersionResponse>(getVersion, []);
  const health = useApiResource<HealthResponse>(getHealth, []);
  const value: SystemState = {
    version: version.data,
    health: health.data,
    loading: version.loading || health.loading,
    error: version.error || health.error,
    reload: () => {
      version.reload();
      health.reload();
    },
  };
  return <SystemCtx.Provider value={value}>{children}</SystemCtx.Provider>;
}

export function useSystem(): SystemState {
  const ctx = useContext(SystemCtx);
  if (!ctx) throw new Error('useSystem must be used within a SystemProvider');
  return ctx;
}
