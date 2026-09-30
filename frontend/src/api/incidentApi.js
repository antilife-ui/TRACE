import { DEMO_MODE, apiGet, mockDelay } from './client.js';
import { generateIncidents } from '../utils/mockData.js';

/** Returns the list of Incidents. */
export async function fetchIncidents() {
  if (DEMO_MODE) return mockDelay(generateIncidents());
  return apiGet('/incidents');
  // Expected contract: [{ id, firstObserved, lastUpdated, riskScore, currentStage, forecastStage, affectedHosts, status }]
}
