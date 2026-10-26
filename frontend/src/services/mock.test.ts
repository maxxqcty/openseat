import { beforeEach, describe, expect, it } from 'vitest'

import { mockApi, resetMock } from './mock'
import { ApiError } from './types'
import type { CreateSessionInput, ErrorCode } from './types'

const HOST_EMAIL = 'host@example.com'
const GUEST_EMAIL = 'guest@example.com'
const PASSWORD = 'password123'

function futureIso(hours: number): string {
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString()
}

function sessionInput(overrides: Partial<CreateSessionInput> = {}): CreateSessionInput {
  return {
    title: 'Risograph Basics',
    description: 'Two-colour prints on paper.',
    startsAt: futureIso(1),
    durationMinutes: 60,
    capacity: 1,
    location: 'Studio C',
    ...overrides,
  }
}

async function loginAs(email: string): Promise<void> {
  await mockApi.auth.login(email, PASSWORD)
}

async function registerGuest(name: string, email: string): Promise<void> {
  await mockApi.auth.register(name, email, PASSWORD)
}

async function expectCode(promise: Promise<unknown>, code: ErrorCode): Promise<void> {
  await expect(promise).rejects.toBeInstanceOf(ApiError)
  await expect(promise).rejects.toMatchObject({ code })
}

beforeEach(() => {
  resetMock()
})

describe('auth', () => {
  it('registers, signs in, returns the profile, and signs out', async () => {
    await expect(mockApi.auth.me()).resolves.toBeNull()

    const registered = await mockApi.auth.register(
      'New Guest',
      'new@example.com',
      PASSWORD,
    )
    expect(registered.displayName).toBe('New Guest')
    expect(registered).not.toHaveProperty('password')

    await expect(mockApi.auth.me()).resolves.toMatchObject({
      email: 'new@example.com',
    })

    await mockApi.auth.logout()
    await expect(mockApi.auth.me()).resolves.toBeNull()

    await expect(
      mockApi.auth.login('new@example.com', 'wrong-password'),
    ).rejects.toMatchObject({ code: 'forbidden' })
  })

  it('rejects duplicate emails, invalid email, and short passwords', async () => {
    await expectCode(
      mockApi.auth.register('Dup', 'host@example.com', PASSWORD),
      'validation_error',
    )
    await expectCode(
      mockApi.auth.register('Bad Email', 'not-an-email', PASSWORD),
      'validation_error',
    )
    await expectCode(
      mockApi.auth.register('Short', 'short@example.com', 'short'),
      'validation_error',
    )
  })
})

describe('sessions', () => {
  it('creates a future session and lists it in start order', async () => {
    await loginAs(HOST_EMAIL)
    const later = await mockApi.sessions.create(
      sessionInput({ title: 'Later Session', startsAt: futureIso(30) }),
    )
    const sooner = await mockApi.sessions.create(
      sessionInput({ title: 'Sooner Session', startsAt: futureIso(2) }),
    )

    const listed = await mockApi.sessions.list()
    const ids = listed.map((session) => session.id)
    expect(ids.indexOf(sooner.id)).toBeLessThan(ids.indexOf(later.id))
  })

  it('rejects invalid field values with validation_error', async () => {
    await loginAs(HOST_EMAIL)

    await expectCode(
      mockApi.sessions.create(sessionInput({ capacity: 0 })),
      'validation_error',
    )
    await expectCode(
      mockApi.sessions.create(sessionInput({ durationMinutes: 5 })),
      'validation_error',
    )
    await expectCode(
      mockApi.sessions.create(sessionInput({ startsAt: futureIso(-1) })),
      'validation_error',
    )
    await expectCode(
      mockApi.sessions.create(sessionInput({ location: 'x' })),
      'validation_error',
    )
  })

  it('returns detail counts and my_booking, and 404s for unknown ids', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 2 }))

    await loginAs(GUEST_EMAIL)
    await mockApi.sessions.book(created.id)

    const detail = await mockApi.sessions.get(created.id)
    expect(detail.confirmedCount).toBe(1)
    expect(detail.checkedInCount).toBe(0)
    expect(detail.waitlistCount).toBe(0)
    expect(detail.myBooking?.status).toBe('confirmed')
    expect(detail.past).toBe(false)

    await mockApi.auth.logout()
    const anonymousDetail = await mockApi.sessions.get(created.id)
    expect(anonymousDetail.myBooking).toBeNull()

    await expectCode(mockApi.sessions.get('missing'), 'not_found')
  })

  it('lets only the host cancel, cancels active bookings, and is idempotent', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 2 }))

    await loginAs(GUEST_EMAIL)
    const booking = await mockApi.sessions.book(created.id)
    await expectCode(mockApi.sessions.cancel(created.id), 'forbidden')

    await loginAs(HOST_EMAIL)
    const cancelled = await mockApi.sessions.cancel(created.id)
    expect(cancelled.status).toBe('cancelled')
    await expect(mockApi.sessions.cancel(created.id)).resolves.toMatchObject({
      status: 'cancelled',
    })

    await loginAs(GUEST_EMAIL)
    const detail = await mockApi.sessions.get(created.id)
    expect(detail.myBooking).toBeNull()
    await expectCode(mockApi.sessions.book(created.id), 'validation_error')

    const roster = await (async () => {
      await loginAs(HOST_EMAIL)
      return mockApi.sessions.roster(created.id)
    })()
    expect(roster.find((entry) => entry.id === booking.id)).toBeUndefined()
  })
})

describe('capacity and waitlist', () => {
  it('confirms up to capacity and waitlists the next request', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 2 }))

    await registerGuest('Guest One', 'one@example.com')
    const first = await mockApi.sessions.book(created.id)
    await registerGuest('Guest Two', 'two@example.com')
    const second = await mockApi.sessions.book(created.id)
    await registerGuest('Guest Three', 'three@example.com')
    const third = await mockApi.sessions.book(created.id)

    expect(first.status).toBe('confirmed')
    expect(second.status).toBe('confirmed')
    expect(third.status).toBe('waitlisted')
    expect(third.waitlistPosition).toBe(1)

    const detail = await mockApi.sessions.get(created.id)
    expect(detail.confirmedCount).toBe(2)
    expect(detail.waitlistCount).toBe(1)
  })

  it('assigns waitlist positions in booking order', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 1 }))

    await loginAs(GUEST_EMAIL)
    await mockApi.sessions.book(created.id)

    await registerGuest('Waiter One', 'w1@example.com')
    const firstWaiter = await mockApi.sessions.book(created.id)
    await registerGuest('Waiter Two', 'w2@example.com')
    const secondWaiter = await mockApi.sessions.book(created.id)

    expect(firstWaiter.waitlistPosition).toBe(1)
    expect(secondWaiter.waitlistPosition).toBe(2)
  })

  it('rejects a second active booking by the same user', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 2 }))

    await loginAs(GUEST_EMAIL)
    await mockApi.sessions.book(created.id)
    await expectCode(mockApi.sessions.book(created.id), 'booking_conflict')
  })

  it('promotes the oldest waiter when a confirmed guest cancels', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 1 }))

    await loginAs(GUEST_EMAIL)
    const first = await mockApi.sessions.book(created.id)
    await registerGuest('Waiter One', 'w1@example.com')
    await mockApi.sessions.book(created.id)
    await registerGuest('Waiter Two', 'w2@example.com')
    await mockApi.sessions.book(created.id)

    await loginAs(GUEST_EMAIL)
    await mockApi.sessions.cancelBooking(first.id)

    await loginAs(HOST_EMAIL)
    const roster = await mockApi.sessions.roster(created.id)
    const promoted = roster.find((entry) => entry.userDisplayName === 'Waiter One')
    const stillWaiting = roster.find((entry) => entry.userDisplayName === 'Waiter Two')

    expect(promoted?.status).toBe('confirmed')
    expect(promoted?.promotedAt).toBeDefined()
    expect(stillWaiting?.status).toBe('waitlisted')
    expect(stillWaiting?.waitlistPosition).toBe(1)
  })

  it('does not promote anyone when a waitlisted booking is cancelled', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 1 }))

    await loginAs(GUEST_EMAIL)
    await mockApi.sessions.book(created.id)
    await registerGuest('Waiter One', 'w1@example.com')
    const waiter = await mockApi.sessions.book(created.id)

    await mockApi.sessions.cancelBooking(waiter.id)

    await loginAs(HOST_EMAIL)
    const roster = await mockApi.sessions.roster(created.id)
    expect(roster).toHaveLength(1)
    expect(roster[0].userDisplayName).toBe('Guest Gale')
  })
})

describe('check-in window', () => {
  it('checks in a confirmed guest inside the two-hour window', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 1 }))

    await loginAs(GUEST_EMAIL)
    const booking = await mockApi.sessions.book(created.id)

    await loginAs(HOST_EMAIL)
    const checkedIn = await mockApi.sessions.checkIn(booking.id)
    expect(checkedIn.status).toBe('checked_in')
    expect(checkedIn.checkedInAt).toBeDefined()

    const again = await mockApi.sessions.checkIn(booking.id)
    expect(again.status).toBe('checked_in')

    const detail = await mockApi.sessions.get(created.id)
    expect(detail.checkedInCount).toBe(1)
    expect(detail.confirmedCount).toBe(0)
  })

  it('rejects check-in before the window opens and for waitlisted bookings', async () => {
    await loginAs(HOST_EMAIL)
    const later = await mockApi.sessions.create(
      sessionInput({ capacity: 1, startsAt: futureIso(6) }),
    )

    await loginAs(GUEST_EMAIL)
    const booking = await mockApi.sessions.book(later.id)

    await loginAs(HOST_EMAIL)
    await expectCode(mockApi.sessions.checkIn(booking.id), 'validation_error')

    const full = await mockApi.sessions.create(
      sessionInput({ capacity: 1, startsAt: futureIso(1) }),
    )
    await loginAs(GUEST_EMAIL)
    await mockApi.sessions.book(full.id)
    await registerGuest('Waiter One', 'w1@example.com')
    const waitlisted = await mockApi.sessions.book(full.id)

    await loginAs(HOST_EMAIL)
    await expectCode(mockApi.sessions.checkIn(waitlisted.id), 'validation_error')
  })

  it('rejects check-in by a guest who is not the host', async () => {
    await loginAs(HOST_EMAIL)
    const created = await mockApi.sessions.create(sessionInput({ capacity: 1 }))

    await loginAs(GUEST_EMAIL)
    const booking = await mockApi.sessions.book(created.id)
    await expectCode(mockApi.sessions.checkIn(booking.id), 'forbidden')
    await expectCode(mockApi.sessions.roster(created.id), 'forbidden')
  })
})
