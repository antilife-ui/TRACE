import { DEMO_MODE, apiGet, mockDelay } from './client.js';
import { generateTelemetry } from '../utils/mockData.js';

/**
 * Returns a page of TelemetryFlow records.
 * Real implementation should use server-side pagination/filtering —
 * never fetch the full flow table into the browser.
 */
export async function fetchTelemetry({ page = 1, pageSize = 50, filters = {} } = {}) {
  if (DEMO_MODE) {
    const all = generateTelemetry(240);
    const filtered = all.filter((f) => {
      if (filters.protocol && f.protocol !== filters.protocol) return false;
      if (filters.minRisk != null && f.riskScore < filters.minRisk) return false;
      return true;
    });
    const start = (page - 1) * pageSize;
    return mockDelay({
      records: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page,
      pageSize,
    });
  }
  const params = new URLSearchParams({ page, pageSize, ...filters });
  return apiGet(`/telemetry?${params.toString()}`);
  // Expected contract: { records: TelemetryFlow[], total, page, pageSize }
}
