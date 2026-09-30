import { DEMO_MODE, apiGet, mockDelay } from './client.js';
import { generateExplanation } from '../utils/mockData.js';

/** Returns the Explanation for a given forecast (feature contributions). */
export async function fetchExplanation(forecastId = 'latest') {
  if (DEMO_MODE) return mockDelay(generateExplanation());
  return apiGet(`/explanations/${forecastId}`);
  // Expected contract: { forecastId, method, features: [{ name, value, contribution, direction }] }
  // If the backend has no explanation available, it should return null —
  // components must render an "EXPLANATION UNAVAILABLE" empty state, never fabricate one.
}
