import { useState } from 'react'
import { api } from '../services'
import type { Booking, MyBooking, RosterEntry } from '../services/types'

export function useBooking() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function book(sessionId: string): Promise<Booking> {
    try {
      setLoading(true)
      setError(null)
      const booking = await api.sessions.book(sessionId)
      return booking
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to book session'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { book, loading, error }
}

export function useCancelBooking() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function cancelBooking(bookingId: string) {
    try {
      setLoading(true)
      setError(null)
      await api.sessions.cancelBooking(bookingId)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to cancel booking'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { cancelBooking, loading, error }
}

export function useRoster(sessionId: string) {
  const [roster, setRoster] = useState<RosterEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setLoading(true)
      setError(null)
      const data = await api.sessions.roster(sessionId)
      setRoster(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load roster')
    } finally {
      setLoading(false)
    }
  }

  return { roster, loading, error, reload: load }
}

export function useCheckIn() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function checkIn(bookingId: string) {
    try {
      setLoading(true)
      setError(null)
      const booking = await api.sessions.checkIn(bookingId)
      return booking
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to check in guest'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { checkIn, loading, error }
}

export function useMyBookings() {
  const [bookings, setBookings] = useState<MyBooking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setLoading(true)
      setError(null)
      const data = await api.me.bookings()
      setBookings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load bookings')
    } finally {
      setLoading(false)
    }
  }

  return { bookings, loading, error, reload: load }
}