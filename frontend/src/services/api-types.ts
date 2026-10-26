/**
 * API DTOs mirroring `openapi.yaml` at the repository root.
 *
 * These are the wire shapes. The service layer maps them onto the UI-facing
 * models in `./types.ts` (camelCase, view-ready). Keep both files in step with
 * the contract; the backend check fails when an endpoint drifts.
 */

export type ApiBookingStatus = 'confirmed' | 'waitlisted' | 'cancelled' | 'checked_in'

export type ApiSessionStatus = 'scheduled' | 'cancelled'

export type ApiErrorCode =
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'booking_conflict'
  | 'validation_error'
  | 'rate_limited'

export interface ApiUser {
  id: string
  email: string
  display_name: string
  created_at: string
}

export interface ApiRegisterRequest {
  display_name: string
  email: string
  password: string
}

export interface ApiLoginRequest {
  email: string
  password: string
}

export interface ApiSession {
  id: string
  host_id: string
  title: string
  description: string
  starts_at: string
  duration_minutes: number
  capacity: number
  location: string
  status: ApiSessionStatus
  created_at: string
  past: boolean
}

export interface ApiSessionCreate {
  title: string
  description?: string
  starts_at: string
  duration_minutes: number
  capacity: number
  location: string
}

export interface ApiBooking {
  id: string
  session_id: string
  user_id: string
  status: ApiBookingStatus
  created_at: string
  promoted_at: string | null
  checked_in_at: string | null
  cancelled_at: string | null
  waitlist_position: number | null
}

export interface ApiSessionDetail extends ApiSession {
  confirmed_count: number
  checked_in_count: number
  waitlist_count: number
  my_booking: ApiBooking | null
}

export interface ApiRosterEntry {
  booking_id: string
  display_name: string
  status: Exclude<ApiBookingStatus, 'cancelled'>
  created_at: string
  checked_in_at: string | null
  waitlist_position: number | null
}

export interface ApiRoster {
  confirmed: ApiRosterEntry[]
  waitlisted: ApiRosterEntry[]
  checked_in: ApiRosterEntry[]
}

export interface ApiMyBooking extends ApiBooking {
  session: ApiSession
}

export interface ApiHealth {
  status: 'ok' | 'degraded'
  version: string
  database: 'not_configured' | 'available' | 'unavailable'
}

export interface ApiErrorBody {
  error: {
    code: ApiErrorCode
    message: string
    details: Record<string, unknown>
  }
}
