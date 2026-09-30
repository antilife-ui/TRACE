import { DEMO_MODE, apiGet, mockDelay } from './client.js';
import { generateModelStatus } from '../utils/mockData.js';

/** Returns ModelStatus — configuration, health, memory, performance metrics. */
export async function fetchModelStatus() {
  if (DEMO_MODE) return mockDelay(generateModelStatus());
  return apiGet('/model/status');
  // Expected contract: see README section "Model Status Contract"
}
