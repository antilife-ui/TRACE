import { useAsync } from './useAsync.js';
import { fetchNetworkState } from '../api/networkApi.js';

export function useNetworkState() {
  return useAsync(fetchNetworkState, [], { pollMs: 15000 });
}
