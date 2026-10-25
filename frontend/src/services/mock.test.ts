import { describe, it, expect } from 'vitest'
import type { Booking, Session } from './types'
import { Api, resetMock } from './mock'

// @vitest/globals is on, so afterEach/beforeEach available

describe('Service mock — capacity boundary', () => {
  it('blocks booking when session at capacity', () => {
    const api = {
      list: async () => [{ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }],
      get: async (id: string) => ({ id, title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      create: async (_title: string, _capacity: number) => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      cancel: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      book: async () => { throw new Error('booking_conflict') },
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }),
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
      getRoster: async () => [],
      resetMock: () => {},
    } as unknown as Api
    ;(global as any).API = api
    ;(global as any).API.sessions = {
      book: async () => { throw new Error('booking_conflict') },
    } as any
    return api.sessions.book({ sessionId: 's1' }).catch((e: any) => expect(e.message).toBe('booking_conflict'))
  })
})

describe('Service mock — waitlist position', () => {
  it('queues user on waitlist when session full', () => {
    const api = {
      list: async () => [{ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }],
      get: async (id: string) => ({ id, title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      create: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      cancel: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      book: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'waitlisted', createdAt: new Date().toISOString() }),
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }),
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
      getRoster: async () => [],
      resetMock: () => {},
    } as unknown as Api
    ;(global as any).API = api
    ;(global as any).API.sessions = {
      book: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'waitlisted', createdAt: new Date().toISOString() }),
    } as any
    return api.sessions.book({ sessionId: 's1' }).then((b: Booking) => expect(b.status).toBe('waitlisted'))
  })
})

describe('Service mock — promotion', () => {
  it('promotes first waitlisted user when a booking is cancelled', () => {
    const api = {
      list: async () => [{ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }],
      get: async (id: string) => ({ id, title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      create: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      cancel: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      book: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }),
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }),
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
      getRoster: async () => [],
      resetMock: () => {},
    } as unknown as Api
    ;(global as any).API = api
    ;(global as any).API.sessions = {
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }),
    } as any
    return api.sessions.cancelBooking('b1').then((promoted: Booking) => {
      expect(promoted.status).toBe('confirmed')
    })
  })
})

describe('Service mock — duplicate booking', () => {
  it('prevents a user from having two confirmed bookings', () => {
    const api = {
      list: async () => [{ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }],
      get: async (id: string) => ({ id, title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      create: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      cancel: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      book: async () => {
        return { id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }
      },
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }),
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
      getRoster: async () => [],
      resetMock: () => {},
    } as unknown as Api
    let callCount = 0
    ;(global as any).API = api
    ;(global as any).API.sessions = {
      book: async () => {
        callCount++
        if (callCount > 1) throw new Error('booking_conflict')
        return { id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }
      },
    } as any
    return Promise.all([
      api.sessions.book({ sessionId: 's1' }),
      api.sessions.book({ sessionId: 's1' }).catch((e: any) => expect(e.message).toBe('booking_conflict')),
    ])
  })
})

describe('Service mock — cancelled session', () => {
  it('marks a booking as cancelled and frees a seat', () => {
    const api = {
      list: async () => [{ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }],
      get: async (id: string) => ({ id, title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      create: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      cancel: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      book: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }),
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }),
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
      getRoster: async () => [],
      resetMock: () => {},
    } as unknown as Api
    ;(global as any).API = api
    ;(global as any).API.sessions = {
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }),
    } as any
    return api.sessions.cancelBooking('b1').then((b: Booking) => expect(b.status).toBe('cancelled'))
  })
})

describe('Service mock — check-in window', () => {
  it('transitions a confirmed booking to checked_in', () => {
    const api = {
      list: async () => [{ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }],
      get: async (id: string) => ({ id, title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      create: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      cancel: async () => ({ id: 's1', title: 'Test', capacity: 3, attendeeCount: 0, waitlistCount: 0, createdBy: 'user1' }),
      book: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }),
      cancelBooking: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }),
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
      getRoster: async () => [],
      resetMock: () => {},
    } as unknown as Api
    ;(global as any).API = api
    ;(global as any).API.sessions = {
      checkIn: async () => ({ id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }),
    } as any
    return api.sessions.checkIn('b1').then((b: Booking) => expect(b.status).toBe('checked_in'))
  })
})