/**
 * Service-layer bootstrap.
 *
 * In development (`import.meta.env.DEV`) the default implementation is the
 * in-memory mock (`services/mock.ts`). A production build defaults to the HTTP
 * client (`services/http.ts`). `VITE_API_MODE` overrides both:
 *
 *   VITE_API_MODE=mock    -> always use the mock
 *   VITE_API_MODE=http    -> always use the HTTP client
 *   (unset)               -> development -> mock, production -> http
 */

import { httpApi } from './http'
import { mockApi, resetMock } from './mock'
import type { Api } from './types'

export * from './types'
export * from './api-types'
export { resetMock }

const requestedMode = import.meta.env.VITE_API_MODE

export const api: Api =
  requestedMode === 'mock'
    ? mockApi
    : requestedMode === 'http'
      ? httpApi
      : import.meta.env.DEV
        ? mockApi
        : httpApi
