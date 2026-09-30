import { useAsync } from './useAsync.js';
import { fetchAttackPath } from '../api/networkApi.js';

export function useAttackPath() {
  return useAsync(fetchAttackPath, []);
}
