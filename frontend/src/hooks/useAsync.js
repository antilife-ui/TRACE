import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Runs an async fetcher, tracks loading/error/data, and exposes refresh().
 * Every page-level hook (useForecast, useNetworkState, etc.) wraps this so
 * loading/error/empty states are handled the same way everywhere.
 */
export function useAsync(fetcher, deps = [], { pollMs } = {}) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const mounted = useRef(true);

  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher()
      .then((data) => {
        if (mounted.current) setState({ data, loading: false, error: null });
      })
      .catch((error) => {
        if (mounted.current) setState({ data: null, loading: false, error });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mounted.current = true;
    run();
    let interval;
    if (pollMs) interval = setInterval(run, pollMs);
    return () => {
      mounted.current = false;
      if (interval) clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, pollMs]);

  return { ...state, refresh: run };
}
