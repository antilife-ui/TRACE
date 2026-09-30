import { useAsync } from './useAsync.js';
import { fetchIncidents } from '../api/incidentApi.js';

export function useIncidents() {
  return useAsync(fetchIncidents, [], { pollMs: 30000 });
}
