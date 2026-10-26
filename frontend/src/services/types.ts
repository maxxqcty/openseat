/**
 * Domain types and the typed service-layer contract.
 *
 * Every API call in the app goes through an `Api` implementation. The mock in
 * `mock.ts` and, from issue #12, the HTTP client in `http.ts` both satisfy this
 * interface.
 */

export type ErrorCode =
  | 'booking_conflict'
  | 'forbidden'
  | 'not_found'
  | 'validation_error'

/** Error thrown by every service implementation with a stable machine code. */
export class ApiError extends Error {
  code: ErrorCode

  constructor(code: ErrorCode, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

export type BookingStatus = 'confirmed' | 'waitlisted' | 'checked_in' | 'cancelled'

export type SessionStatus = 'scheduled' | 'cancelled'

export interface User {
  id: string
  displayName: string
  email: string
}

export interface Session {
  id: string
  hostId: string
  title: string
  description: string
  startsAt: string
  durationMinutes: number
  capacity: number
  location: string
  status: SessionStatus
  createdAt: string
}

export interface SessionDetail extends Session {
  past: boolean
  confirmedCount: number
  checkedInCount: number
  waitlistCount: number
  myBooking: Booking | null
}

export interface CreateSessionInput {
  title: string
  description?: string
  startsAt: string
  durationMinutes: number
  capacity: number
  location?: string
}

export interface Booking {
  id: string
  sessionId: string
  userId: string
  userDisplayName: string
  status: BookingStatus
  createdAt: string
  checkedInAt?: string
  promotedAt?: string
  waitlistPosition?: number
}

export interface AuthApi {
  register(displayName: string, email: string, password: string): Promise<User>
  login(email: string, password: string): Promise<User>
  logout(): Promise<void>
  me(): Promise<User | null>
}

export interface SessionsApi {
  list(): Promise<Session[]>
  get(id: string): Promise<SessionDetail>
  create(input: CreateSessionInput): Promise<Session>
  cancel(id: string): Promise<Session>
  book(sessionId: string): Promise<Booking>
  cancelBooking(bookingId: string): Promise<Booking>
  roster(sessionId: string): Promise<Booking[]>
  checkIn(bookingId: string): Promise<Booking>
}

export interface Api {
  auth: AuthApi
  sessions: SessionsApi
}
