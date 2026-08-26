// POST-style action hook: run(args) with pending/error/result state. Errors surface the backend detail.
import { useCallback, useState } from 'react';
import { toApiError, type ApiError } from '../services/apiClient';

export interface AsyncActionState<TArgs, TResult> {
  run: (args: TArgs) => Promise<void>;
  pending: boolean;
  error?: ApiError;
  result?: TResult;
  reset: () => void;
}

export function useAsyncAction<TArgs, TResult>(
  action: (args: TArgs) => Promise<TResult>,
): AsyncActionState<TArgs, TResult> {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | undefined>();
  const [result, setResult] = useState<TResult | undefined>();

  const run = useCallback(
    async (args: TArgs) => {
      setPending(true);
      setError(undefined);
      try {
        const r = await action(args);
        setResult(r);
      } catch (err) {
        setError(toApiError(err));
      } finally {
        setPending(false);
      }
    },
    [action],
  );

  const reset = useCallback(() => {
    setError(undefined);
    setResult(undefined);
  }, []);

  return { run, pending, error, result, reset };
}
