/**
 * HTTP implementation placeholder.
 *
 * Issue #3 only defines the seam: `index.ts` selects this client in production
 * builds. The real `fetch` calls are implemented in issue #12, so every method
 * currently fails loudly instead of silently returning fake data in production.
 */

import { ApiError } from './types'
import type { Api } from './types'

function notImplemented(): never {
  throw new ApiError(
    'validation_error',
    'The HTTP client is implemented in issue #12',
  )
}

export const httpApi: Api = {
  auth: {
    async register() {
      notImplemented()
    },
    async login() {
      notImplemented()
    },
    async logout() {
      notImplemented()
    },
    async me() {
      notImplemented()
    },
  },
  sessions: {
    async list() {
      notImplemented()
    },
    async get() {
      notImplemented()
    },
    async create() {
      notImplemented()
    },
    async cancel() {
      notImplemented()
    },
    async book() {
      notImplemented()
    },
    async cancelBooking() {
      notImplemented()
    },
    async roster() {
      notImplemented()
    },
    async checkIn() {
      notImplemented()
    },
  },
}
