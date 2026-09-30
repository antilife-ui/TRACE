import { useAsync } from './useAsync.js';
import { fetchExplanation } from '../api/explanationApi.js';

export function useExplanation(forecastId = 'latest') {
  return useAsync(() => fetchExplanation(forecastId), [forecastId]);
}
