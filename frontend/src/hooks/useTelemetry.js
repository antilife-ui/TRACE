import { useState } from 'react';
import { useAsync } from './useAsync.js';
import { fetchTelemetry } from '../api/telemetryApi.js';

export function useTelemetry() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({});
  const pageSize = 25;

  const { data, loading, error, refresh } = useAsync(
    () => fetchTelemetry({ page, pageSize, filters }),
    [page, filters]
  );

  return {
    records: data?.records ?? [],
    total: data?.total ?? 0,
    page,
    pageSize,
    filters,
    setFilters: (f) => {
      setPage(1);
      setFilters(f);
    },
    setPage,
    loading,
    error,
    refresh,
  };
}
