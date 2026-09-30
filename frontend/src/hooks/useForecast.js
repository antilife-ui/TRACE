import { useAsync } from './useAsync.js';
import { fetchForecast, fetchRiskTimeline, fetchAttackStages } from '../api/forecastApi.js';

export function useForecast(horizon = 5) {
  return useAsync(() => fetchForecast(horizon), [horizon], { pollMs: 20000 });
}

export function useRiskTimeline() {
  return useAsync(fetchRiskTimeline, [], { pollMs: 20000 });
}

export function useAttackStages() {
  return useAsync(fetchAttackStages, [], { pollMs: 20000 });
}
