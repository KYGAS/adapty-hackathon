import { useCallback, useEffect, useRef, useState } from 'react';

export interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  reload: () => void;
}

/** Small data hook: runs the loader when the deps change, exposes reload(), ignores stale answers. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    const id = ++latest.current;
    setLoading(true);
    setError(null);
    loader()
      .then((result) => {
        if (latest.current === id) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (latest.current === id) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
