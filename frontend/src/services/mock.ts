/**
 * In-memory implementation of the service layer.
 *
 * Used when `VITE_API_MODE=mock` and by the frontend test suite. The mock owns
 * its module-level data, enforces the domain rules from `_docs/spec.md` §4, and
 * returns the same error codes as the API contract in `http.ts`.
 */

import { ApiError } from './types'
import type {
  Api,
  Booking,
  CreateSessionInput,
  RosterEntry,
  Session,
  SessionDetail,
  User,
} from './types'

const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const CHECK_IN_WINDOW_MS = 2 * HOUR

const MIN_DURATION = 15
const MAX_DURATION = 480
const MIN_CAPACITY = 1
const MAX_CAPACITY = 100

interface MockUser extends User {
  password: string
}

/** Bookings carry a display name internally; the wire type never exposes it. */
interface MockBooking extends Booking {
  userDisplayName: string
}

interface MockState {
  users: MockUser[]
  sessions: Session[]
  bookings: MockBooking[]
  currentUserId: string | null
}

let idCounter = 0
let state: MockState = createSeedState()

function nextId(prefix: string): string {
  idCounter += 1
  return `${prefix}${String(idCounter).padStart(6, '0')}`
}

function isoIn(ms: number): string {
  return new Date(Date.now() + ms).toISOString()
}

function createSeedState(): MockState {
  idCounter = 0
  const host: MockUser = {
    id: nextId('u'),
    displayName: 'Host Harper',
    email: 'host@example.com',
    password: 'password123',
  }
  const guest: MockUser = {
    id: nextId('u'),
    displayName: 'Guest Gale',
    email: 'guest@example.com',
    password: 'password123',
  }

  const openSession: Session = {
    id: nextId('s'),
    hostId: host.id,
    title: 'Intro to Screen Printing',
    description: 'Bring a shirt and leave with a print.',
    startsAt: isoIn(HOUR),
    durationMinutes: 90,
    capacity: 2,
    location: 'Studio A',
    status: 'scheduled',
    createdAt: new Date().toISOString(),
  }
  const fullSession: Session = {
    id: nextId('s'),
    hostId: host.id,
    title: 'Sold Out Bookbinding',
    description: 'A full session for waitlist demos.',
    startsAt: isoIn(24 * HOUR),
    durationMinutes: 60,
    capacity: 1,
    location: 'Studio B',
    status: 'scheduled',
    createdAt: new Date().toISOString(),
  }
  const booked: MockBooking = {
    id: nextId('b'),
    sessionId: fullSession.id,
    userId: guest.id,
    userDisplayName: guest.displayName,
    status: 'confirmed',
    createdAt: new Date().toISOString(),
  }

  return {
    users: [host, guest],
    sessions: [openSession, fullSession],
    bookings: [booked],
    currentUserId: null,
  }
}

/** Restore deterministic seed data. Intended for tests. */
export function resetMock(): void {
  state = createSeedState()
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function toPublicUser(user: MockUser): User {
  return { id: user.id, displayName: user.displayName, email: user.email }
}

function currentUser(): MockUser | null {
  if (!state.currentUserId) return null
  return state.users.find((user) => user.id === state.currentUserId) ?? null
}

function requireUser(): MockUser {
  const user = currentUser()
  if (!user) {
    // Mirrors the API, which answers 401 when there is no session cookie.
    throw new ApiError('unauthorized', 'Sign in required')
  }
  return user
}

function findSession(sessionId: string): Session {
  const session = state.sessions.find((candidate) => candidate.id === sessionId)
  if (!session) {
    throw new ApiError('not_found', 'Session not found')
  }
  return session
}

function findBooking(bookingId: string): MockBooking {
  const booking = state.bookings.find((candidate) => candidate.id === bookingId)
  if (!booking) {
    throw new ApiError('not_found', 'Booking not found')
  }
  return booking
}

function isPast(session: Session): boolean {
  const endsAt = Date.parse(session.startsAt) + session.durationMinutes * MINUTE
  return Date.now() > endsAt
}

function occupiesSeat(booking: Booking): boolean {
  return booking.status === 'confirmed' || booking.status === 'checked_in'
}

function activeBookings(sessionId: string): MockBooking[] {
  return state.bookings
    .filter(
      (booking) =>
        booking.sessionId === sessionId &&
        booking.status !== 'cancelled',
    )
    .sort(compareBookings)
}

function compareBookings(left: Booking, right: Booking): number {
  const byCreated = left.createdAt.localeCompare(right.createdAt)
  if (byCreated !== 0) return byCreated
  return left.id.localeCompare(right.id)
}

function waitlistOrder(sessionId: string): MockBooking[] {
  return state.bookings
    .filter(
      (booking) =>
        booking.sessionId === sessionId && booking.status === 'waitlisted',
    )
    .sort(compareBookings)
}

function assignWaitlistPositions(sessionId: string): void {
  waitlistOrder(sessionId).forEach((booking, index) => {
    booking.waitlistPosition = index + 1
  })
}

function occupiedCount(sessionId: string): number {
  return state.bookings.filter(
    (booking) => booking.sessionId === sessionId && occupiesSeat(booking),
  ).length
}

function promoteOldestWaiter(sessionId: string): void {
  const session = findSession(sessionId)
  if (session.status === 'cancelled' || isPast(session)) return
  if (occupiedCount(sessionId) >= session.capacity) return

  const [oldest] = waitlistOrder(sessionId)
  if (!oldest) return

  oldest.status = 'confirmed'
  oldest.promotedAt = new Date().toISOString()
  delete oldest.waitlistPosition
  assignWaitlistPositions(sessionId)
}

/** Reject a roster row that is no longer active; the API never returns these. */
function rosterStatus(booking: MockBooking): RosterEntry['status'] {
  if (booking.status === 'cancelled') {
    throw new Error('cancelled bookings are not part of a roster')
  }
  return booking.status
}

function toRosterEntry(booking: MockBooking): RosterEntry {
  return {
    bookingId: booking.id,
    displayName: booking.userDisplayName,
    status: rosterStatus(booking),
    createdAt: booking.createdAt,
    checkedInAt: booking.checkedInAt,
    waitlistPosition: booking.waitlistPosition,
  }
}

function sessionDetail(session: Session): SessionDetail {
  const user = currentUser()
  const bookings = activeBookings(session.id)
  const mine = user
    ? bookings.find((booking) => booking.userId === user.id) ?? null
    : null

  return {
    ...session,
    past: isPast(session),
    confirmedCount: bookings.filter((booking) => booking.status === 'confirmed')
      .length,
    checkedInCount: bookings.filter(
      (booking) => booking.status === 'checked_in',
    ).length,
    waitlistCount: bookings.filter((booking) => booking.status === 'waitlisted')
      .length,
    myBooking: mine,
  }
}

function validationError(message: string): never {
  throw new ApiError('validation_error', message)
}

function assertFutureStart(startsAt: string): void {
  const parsed = Date.parse(startsAt)
  if (Number.isNaN(parsed)) {
    validationError('Start time must be a valid ISO 8601 timestamp')
  }
  if (parsed <= Date.now()) {
    validationError('Start time must be in the future')
  }
}

function passwordIsValid(password: string): boolean {
  return password.length >= 8
}

function normaliseEmail(email: string): string {
  return email.trim().toLowerCase()
}

function emailIsValid(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

// ---------------------------------------------------------------------------
// auth
// ---------------------------------------------------------------------------

const auth: Api['auth'] = {
  async register(displayName, email, password) {
    const name = displayName.trim()
    const address = normaliseEmail(email)

    if (name.length === 0) {
      validationError('Display name is required')
    }
    if (!emailIsValid(address)) {
      validationError('Enter a valid email address')
    }
    if (!passwordIsValid(password)) {
      validationError('Password must be at least 8 characters')
    }
    if (state.users.some((user) => user.email === address)) {
      validationError('Email already registered')
    }

    const user: MockUser = {
      id: nextId('u'),
      displayName: name,
      email: address,
      password,
    }
    state.users.push(user)
    state.currentUserId = user.id
    return toPublicUser(user)
  },

  async login(email, password) {
    const address = normaliseEmail(email)
    const user = state.users.find((candidate) => candidate.email === address)
    if (!user || user.password !== password) {
      throw new ApiError('forbidden', 'Incorrect email or password')
    }
    state.currentUserId = user.id
    return toPublicUser(user)
  },

  async logout() {
    state.currentUserId = null
  },

  async me() {
    const user = currentUser()
    return user ? toPublicUser(user) : null
  },
}

// ---------------------------------------------------------------------------
// sessions and bookings
// ---------------------------------------------------------------------------

const sessions: Api['sessions'] = {
  async list() {
    return state.sessions
      .filter((session) => session.status === 'scheduled' && !isPast(session))
      .sort((left, right) => left.startsAt.localeCompare(right.startsAt))
  },

  async get(id) {
    return sessionDetail(findSession(id))
  },

  async create(input: CreateSessionInput) {
    const host = requireUser()
    const title = input.title.trim()
    const description = (input.description ?? '').trim()
    const location = (input.location ?? '').trim()

    if (title.length < 3 || title.length > 120) {
      validationError('Title must be between 3 and 120 characters')
    }
    if (description.length > 2000) {
      validationError('Description must be 2000 characters or fewer')
    }
    if (location.length < 3 || location.length > 200) {
      validationError('Location must be between 3 and 200 characters')
    }
    assertFutureStart(input.startsAt)
    if (
      !Number.isInteger(input.durationMinutes) ||
      input.durationMinutes < MIN_DURATION ||
      input.durationMinutes > MAX_DURATION
    ) {
      validationError(
        `Duration must be between ${MIN_DURATION} and ${MAX_DURATION} minutes`,
      )
    }
    if (
      !Number.isInteger(input.capacity) ||
      input.capacity < MIN_CAPACITY ||
      input.capacity > MAX_CAPACITY
    ) {
      validationError(
        `Capacity must be between ${MIN_CAPACITY} and ${MAX_CAPACITY}`,
      )
    }

    const session: Session = {
      id: nextId('s'),
      hostId: host.id,
      title,
      description,
      startsAt: input.startsAt,
      durationMinutes: input.durationMinutes,
      capacity: input.capacity,
      location,
      status: 'scheduled',
      createdAt: new Date().toISOString(),
    }
    state.sessions.push(session)
    return session
  },

  async cancel(id) {
    const user = requireUser()
    const session = findSession(id)
    if (session.hostId !== user.id) {
      throw new ApiError('forbidden', 'Only the host can cancel this session')
    }
    if (session.status === 'cancelled') {
      return session
    }

    session.status = 'cancelled'
    state.bookings
      .filter(
        (booking) =>
          booking.sessionId === session.id &&
          booking.status !== 'cancelled',
      )
      .forEach((booking) => {
        booking.status = 'cancelled'
        delete booking.waitlistPosition
      })
    return session
  },

  async book(sessionId) {
    const user = requireUser()
    const session = findSession(sessionId)

    if (session.status === 'cancelled' || isPast(session)) {
      validationError('This session is no longer bookable')
    }

    const mine = activeBookings(sessionId).find(
      (booking) => booking.userId === user.id,
    )
    if (mine) {
      throw new ApiError(
        'booking_conflict',
        'You already have an active booking for this session',
      )
    }

    const booking: MockBooking = {
      id: nextId('b'),
      sessionId,
      userId: user.id,
      userDisplayName: user.displayName,
      status: 'confirmed',
      createdAt: new Date().toISOString(),
    }

    if (occupiedCount(sessionId) >= session.capacity) {
      booking.status = 'waitlisted'
    }

    state.bookings.push(booking)
    assignWaitlistPositions(sessionId)
    return booking
  },

  async cancelBooking(bookingId) {
    const user = requireUser()
    const booking = findBooking(bookingId)

    if (booking.userId !== user.id) {
      throw new ApiError('forbidden', 'You can only cancel your own booking')
    }
    if (booking.status === 'cancelled') {
      return
    }
    if (booking.status === 'checked_in') {
      validationError('A checked-in booking cannot be cancelled')
    }

    const heldSeat = occupiesSeat(booking)
    booking.status = 'cancelled'
    delete booking.waitlistPosition

    if (heldSeat) {
      promoteOldestWaiter(booking.sessionId)
    } else {
      assignWaitlistPositions(booking.sessionId)
    }
  },

  async roster(sessionId) {
    const user = requireUser()
    const session = findSession(sessionId)
    if (session.hostId !== user.id) {
      throw new ApiError('forbidden', 'Only the host can view the roster')
    }

    const order: Record<RosterEntry['status'], number> = {
      confirmed: 0,
      checked_in: 1,
      waitlisted: 2,
    }

    return activeBookings(sessionId)
      .sort((left, right) => {
        const byStatus = order[rosterStatus(left)] - order[rosterStatus(right)]
        return byStatus !== 0 ? byStatus : compareBookings(left, right)
      })
      .map(toRosterEntry)
  },

  async checkIn(bookingId) {
    const user = requireUser()
    const booking = findBooking(bookingId)
    const session = findSession(booking.sessionId)

    if (session.hostId !== user.id) {
      throw new ApiError('forbidden', 'Only the host can check guests in')
    }
    if (booking.status === 'checked_in') {
      return booking
    }
    if (booking.status !== 'confirmed') {
      validationError('Only confirmed bookings can be checked in')
    }

    const start = Date.parse(session.startsAt)
    const end = start + session.durationMinutes * MINUTE
    const now = Date.now()
    if (now < start - CHECK_IN_WINDOW_MS || now > end) {
      validationError('Check-in is not open for this session')
    }

    booking.status = 'checked_in'
    booking.checkedInAt = new Date().toISOString()
    return booking
  },
}

const me: Api['me'] = {
  async bookings() {
    const user = requireUser()
    return state.bookings
      .filter((booking) => booking.userId === user.id)
      .map((booking) => ({
        id: booking.id,
        sessionId: booking.sessionId,
        userId: booking.userId,
        status: booking.status,
        createdAt: booking.createdAt,
        checkedInAt: booking.checkedInAt,
        promotedAt: booking.promotedAt,
        waitlistPosition: booking.waitlistPosition,
        session: findSession(booking.sessionId),
      }))
      .sort(
        (left, right) =>
          left.session.startsAt.localeCompare(right.session.startsAt) ||
          left.createdAt.localeCompare(right.createdAt) ||
          left.id.localeCompare(right.id),
      )
  },
}

export const mockApi: Api = { auth, sessions, me }
