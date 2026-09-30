import { DEMO_MODE, apiGet, mockDelay } from './client.js';
import { generateForecast, generateRiskTimeline, generateAttackStages } from '../utils/mockData.js';

/** Returns the K-step Forecast object. */
export async function fetchForecast(horizon = 5) {
  if (DEMO_MODE) return mockDelay(generateForecast(horizon));
  return apiGet(`/forecast?horizon=${horizon}`);
  // Expected contract: { generatedAt, currentWindowId, horizon, riskScore, states: [...] }
}

/** Returns the combined observed + predicted risk timeline. */
export async function fetchRiskTimeline() {
  if (DEMO_MODE) return mockDelay(generateRiskTimeline());
  return apiGet('/forecast/risk-timeline');
  // Expected contract: [{ timestamp, value, kind: 'observed' | 'predicted' }]
}

/** Returns the attack-stage progression (observed / current / predicted). */
export async function fetchAttackStages() {
  if (DEMO_MODE) return mockDelay(generateAttackStages());
  return apiGet('/forecast/attack-stages');
  // Expected contract: [{ name, status, score, confidence, windowId }]
}
