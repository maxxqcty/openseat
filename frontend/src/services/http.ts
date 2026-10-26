/**
 * HTTP implementation of the service layer.
 *
 * Every call goes to the FastAPI backend on the same origin, sending the
 * HttpOnly session cookie (`credentials: "include"`). Mutations carry
 * `X-Requested-With: openseat`, which the API requires as its CSRF defence
 * (`_docs/spec.md` §5.1). Error responses follow the `{ error: { code,
 * message, details } }` shape from `_docs/spec.md` §6 and are rethrown as
 * `ApiError`, so pages branch on a stable machine code instead of response
 * text. This file is the only place in the app that calls `fetch`.
 */

import type {
  ApiBooking,
  ApiErrorBody,
  ApiMyBooking,
  ApiRoster,
  ApiRosterEntry,
  ApiSession,
  ApiSessionDetail,
  ApiUser,
} from './api-types'
import { ApiError } from './types'
import type {
  Api,
  Booking,
  ErrorCode,
  MeApi,
  MyBooking,
  RosterEntry,
  Session,
  SessionDetail,
  User,
} from './types'

const API_BASE = '/api'
const CSRF_HEADER = 'X-Requested-With'
const CSRF_VALUE = 'openseat'
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

const KNOWN_ERROR_CODES = new Set<string>([
  'booking_conflict',
  'conflict',
  'forbidden',
  'network_error',
  'not_found',
  'rate_limited',
  'unauthorized',
  'validation_error',
])

function errorCodeFor(status: number, wireCode: unknown): ErrorCode {
  if (typeof wireCode === 'string' && KNOWN_ERROR_CODES.has(wireCode)) {
    return wireCode as ErrorCode
  }
  if (status === 400 || status === 422) return 'validation_error'
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'not_found'
  if (status === 409) return 'conflict'
  if (status === 429) return 'rate_limited'
  if (status >= 500) return 'network_error'
  return 'validation_error'
}

function messageFor(status: number, body: ApiErrorBody | null): string {
  if (body?.error?.message) return body.error.message
  if (status >= 500) return 'The server could not complete the request. Try again.'
  if (status === 401) return 'Sign in to continue.'
  if (status === 403) return 'You do not have permission to do that.'
  if (status === 404) return 'That item no longer exists.'
  if (status === 409) return 'That request conflicts with the current state.'
  if (status === 429) return 'Too many requests. Wait a moment and try again.'
  return `Request failed with status ${status}.`
}

function parseBody(text: string): ApiErrorBody | null {
  if (!text) return null
  try {
    const parsed: unknown = JSON.parse(text)
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'error' in parsed &&
      typeof (parsed as { error: unknown }).error === 'object'
    ) {
      return parsed as ApiErrorBody
    }
    return null
  } catch {
    return null
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (MUTATING_METHODS.has(method)) headers[CSRF_HEADER] = CSRF_VALUE
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      credentials: 'include',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('network_error', 'Could not reach the server. Check your connection.')
  }

  const text = await response.text()

  if (!response.ok) {
    const parsed = parseBody(text)
    throw new ApiError(
      errorCodeFor(response.status, parsed?.error?.code),
      messageFor(response.status, parsed),
    )
  }

  if (!text) return undefined as T
  return JSON.parse(text) as T
}

// ---------------------------------------------------------------------------
// wire (snake_case DTOs) -> UI (camelCase models)
// ---------------------------------------------------------------------------

function toUser(dto: ApiUser): User {
  return { id: dto.id, displayName: dto.display_name, email: dto.email }
}

function toSession(dto: ApiSession): Session {
  return {
    id: dto.id,
    hostId: dto.host_id,
    title: dto.title,
    description: dto.description,
    startsAt: dto.starts_at,
    durationMinutes: dto.duration_minutes,
    capacity: dto.capacity,
    location: dto.location,
    status: dto.status,
    createdAt: dto.created_at,
  }
}

function toBooking(dto: ApiBooking): Booking {
  return {
    id: dto.id,
    sessionId: dto.session_id,
    userId: dto.user_id,
    status: dto.status,
    createdAt: dto.created_at,
    promotedAt: dto.promoted_at ?? undefined,
    checkedInAt: dto.checked_in_at ?? undefined,
    waitlistPosition: dto.waitlist_position ?? undefined,
  }
}

function toSessionDetail(dto: ApiSessionDetail): SessionDetail {
  return {
    ...toSession(dto),
    past: dto.past,
    confirmedCount: dto.confirmed_count,
    checkedInCount: dto.checked_in_count,
    waitlistCount: dto.waitlist_count,
    myBooking: dto.my_booking ? toBooking(dto.my_booking) : null,
  }
}

function toRosterEntry(dto: ApiRosterEntry): RosterEntry {
  return {
    bookingId: dto.booking_id,
    displayName: dto.display_name,
    status: dto.status,
    createdAt: dto.created_at,
    checkedInAt: dto.checked_in_at ?? undefined,
    waitlistPosition: dto.waitlist_position ?? undefined,
  }
}

function toMyBooking(dto: ApiMyBooking): MyBooking {
  return { ...toBooking(dto), session: toSession(dto.session) }
}

function encode(id: string): string {
  return encodeURIComponent(id)
}

/** The signed-in user's profile, or `null` when there is no session cookie. */
async function fetchMe(): Promise<User | null> {
  try {
    return toUser(await request<ApiUser>('GET', '/auth/me'))
  } catch (error) {
    if (error instanceof ApiError && error.code === 'unauthorized') return null
    throw error
  }
}

// ---------------------------------------------------------------------------
// Api implementations
// ---------------------------------------------------------------------------

const auth: Api['auth'] = {
  async register(displayName, email, password) {
    const user = await request<ApiUser>('POST', '/auth/register', {
      display_name: displayName,
      email,
      password,
    })
    return toUser(user)
  },

  async login(email, password) {
    await request<void>('POST', '/auth/login', { email, password })
    const user = await fetchMe()
    if (!user) {
      throw new ApiError('unauthorized', 'Sign in failed. Try again.')
    }
    return user
  },

  async logout() {
    await request<void>('POST', '/auth/logout')
  },

  async me() {
    return fetchMe()
  },
}

const sessions: Api['sessions'] = {
  async list() {
    const list = await request<ApiSession[]>('GET', '/sessions')
    return list.map(toSession)
  },

  async get(id) {
    return toSessionDetail(await request<ApiSessionDetail>('GET', `/sessions/${encode(id)}`))
  },

  async create(input) {
    const created = await request<ApiSession>('POST', '/sessions', {
      title: input.title,
      description: input.description ?? '',
      starts_at: input.startsAt,
      duration_minutes: input.durationMinutes,
      capacity: input.capacity,
      location: input.location ?? '',
    })
    return toSession(created)
  },

  async cancel(id) {
    const detail = await request<ApiSessionDetail>('POST', `/sessions/${encode(id)}/cancel`)
    return toSessionDetail(detail)
  },

  async book(sessionId) {
    const booking = await request<ApiBooking>(
      'POST',
      `/sessions/${encode(sessionId)}/bookings`,
    )
    return toBooking(booking)
  },

  async cancelBooking(bookingId) {
    await request<void>('DELETE', `/bookings/${encode(bookingId)}`)
  },

  async roster(sessionId) {
    const roster = await request<ApiRoster>('GET', `/sessions/${encode(sessionId)}/bookings`)
    return [...roster.confirmed, ...roster.waitlisted, ...roster.checked_in].map(toRosterEntry)
  },

  async checkIn(bookingId) {
    const booking = await request<ApiBooking>('POST', `/bookings/${encode(bookingId)}/check-in`)
    return toBooking(booking)
  },
}

const me: MeApi = {
  async bookings() {
    const list = await request<ApiMyBooking[]>('GET', '/me/bookings')
    return list.map(toMyBooking)
  },
}

export const httpApi: Api = { auth, sessions, me }
