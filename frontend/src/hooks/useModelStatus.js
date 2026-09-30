import { useAsync } from './useAsync.js';
import { fetchModelStatus } from '../api/modelApi.js';

export function useModelStatus() {
  return useAsync(fetchModelStatus, [], { pollMs: 30000 });
}
