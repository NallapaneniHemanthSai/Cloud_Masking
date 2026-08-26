// GET-style data hook exposing explicit loading / error / data / empty states + a reload().
import { useCallback, useEffect, useState } from 'react';
import { toApiError, type ApiError } from '../services/apiClient';

export interface ApiResourceState<T> {
  data?: T;
  error?: ApiError;
  loading: boolean;
  reload: () => void;
}

export function useApiResource<T>(fetcher: () => Promise<T>, deps: unknown[] = []): ApiResourceState<T> {
  const [state, setState] = useState<{ data?: T; error?: ApiError; loading: boolean }>({
    loading: true,
  });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const reload = useCallback(() => {
    let cancelled = false;
    setState({ loading: true });
    fetcher()
      .then((data) => !cancelled && setState({ data, loading: false }))
      .catch((err) => !cancelled && setState({ error: toApiError(err), loading: false }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    const cancel = reload();
    return cancel;
  }, [reload]);

  return { ...state, reload };
}
