/**
 * Service-layer bootstrap.
 *
 * In development (Vite `mode: 'development'`) the default implementation is the
 * in-memory mock (`services/mock.ts`). In a production build the default switches
 * to an HTTP client (`services/http.ts`).  The environment variable
 * `VITE_API_MODE` overrides both values:
 *
 *   VITE_API_MODE=mock    → always use the mock
 *   VITE_API_MODE=http    → always use the HTTP client
 *   (unset)               → development → mock, production → http
 */

export * from './types'
export * from './api-types'

// Development default: mock object (re-exported from ./mock)
export type { Api } from './mock'