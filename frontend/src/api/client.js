// Central API client.
//
// DEMO_MODE controls whether the app serves mock data (matching the real
// contract shapes) or calls the live backend. Flip it with an env var once
// the backend is ready — no component code needs to change, because every
// page consumes data through src/hooks/*, which call src/api/*, which call
// this client.
//
// To connect a real backend:
//   1. Set VITE_API_BASE_URL in a .env file (e.g. http://localhost:8000/api)
//   2. Set VITE_DEMO_MODE=false
//   3. Each function in src/api/*.js already has the real fetch call
//      written and commented — uncomment it and delete the mock branch.

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== 'false';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const MOCK_LATENCY_MS = 380;

/** Simulates network latency so loading states are visible/testable in demo mode. */
export function mockDelay(value, ms = MOCK_LATENCY_MS) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function apiGet(path, { signal } = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!res.ok) {
    throw new ApiError(`Request to ${path} failed with status ${res.status}`, res.status);
  }
  return res.json();
}
