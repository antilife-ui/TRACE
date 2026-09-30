import { DEMO_MODE, apiGet, mockDelay } from './client.js';
import { generateNetworkState, generateAttackPath } from '../utils/mockData.js';

/** Returns the current NetworkState object. */
export async function fetchNetworkState() {
  if (DEMO_MODE) return mockDelay(generateNetworkState());
  return apiGet('/network/state');
  // Expected contract: { timestamp, windowId, riskScore, stage, metrics, features }
}

/** Returns the AttackPath graph (nodes + observed/predicted edges). */
export async function fetchAttackPath() {
  if (DEMO_MODE) return mockDelay(generateAttackPath());
  return apiGet('/network/attack-path');
  // Expected contract: { nodes: [...], edges: [{ source, target, kind, riskScore }] }
}
