import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, useMyBookings, useCancelBooking } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { formatDateTime, hasSessionEnded } from '../lib/date'
import { DateBadge } from '../components/DateBadge'
import { accentFor } from '../lib/accent'

function getStatusLabel(status: string, waitlistPosition?: number): string {
  switch (status) {
    case 'confirmed': return 'Confirmed'
    case 'waitlisted': return `Waitlisted, position ${waitlistPosition ?? '?'}`
    case 'checked_in': return 'Checked in'
    case 'cancelled': return 'Cancelled'
    default: return status
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'confirmed': return 'text-green-700 bg-green-50'
    case 'waitlisted': return 'text-text bg-muted/10'
    case 'checked_in': return 'text-white bg-primary-dark'
    case 'cancelled': return 'text-muted bg-muted/20'
    default: return 'text-text bg-card'
  }
}

export function MyBookingsPage() {
  const { user, loading: authLoading } = useAuth()
  const { bookings, error, reload } = useMyBookings()
  const [now] = useState(() => Date.now())
  const { cancelBooking, loading: cancellingLoading } = useCancelBooking()
  const navigate = useNavigate()
  const [cancellingBookingId, setCancellingBookingId] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      navigate(`/login?returnTo=${encodeURIComponent('/me')}`, { replace: true })
    }
  }, [user, authLoading, navigate])

  if (authLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-2xl border border-muted/15 bg-card shadow-[var(--shadow-card)] p-8 text-center">
          <div className="inline-flex items-center gap-2 text-muted">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Loading…</span>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  async function handleCancel(bookingId: string) {
    setCancellingBookingId(bookingId)
    try {
      await cancelBooking(bookingId)
      reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Cancellation failed')
    } finally {
      setCancellingBookingId(null)
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState
          title="Could not load bookings"
          message={error}
          action={<Button onClick={reload} variant="secondary">Try again</Button>}
        />
      </div>
    )
  }

  const isPast = (b: (typeof bookings)[number]) =>
    b.status === 'cancelled' || hasSessionEnded(b.session.startsAt, b.session.durationMinutes, now)
  const activeBookings = bookings.filter((b) => !isPast(b))
  const pastBookings = bookings.filter(isPast)

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-4xl font-bold tracking-tight text-text">My bookings</h1>
      <p className="mt-2 text-muted">Your seats and waitlist spots, in one place.</p>

      {activeBookings.length === 0 && pastBookings.length === 0 ? (
        <EmptyState
          title="No bookings yet"
          message="Find an event and book a seat to get started."
          action={<Link to="/sessions" className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-surface hover:bg-primary/90">See events</Link>}
        />
      ) : (
        <>
          {activeBookings.length > 0 && (
            <section className="mt-8">
              <h2 className="text-lg font-semibold text-text">Upcoming</h2>
              <ul className="mt-4 space-y-3" role="list">
                {activeBookings.map((booking) => (
                  <li key={booking.id} className="rounded-2xl border border-muted/15 bg-card shadow-[var(--shadow-card)] p-4">
                    <div className="flex items-start gap-4">
                      <DateBadge iso={booking.session.startsAt} accent={accentFor(booking.session.id)} />
                      <div className="min-w-0 flex-1">
                        <Link to={`/sessions/${booking.session.id}`} className="font-semibold text-text hover:text-primary">
                          {booking.session.title}
                        </Link>
                        <p className="mt-1 text-sm text-muted">{booking.session.location}</p>
                        <p className="text-sm text-text">{formatDateTime(booking.session.startsAt)} ({booking.session.durationMinutes} min)</p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${getStatusColor(booking.status)}`}>
                          {getStatusLabel(booking.status, booking.waitlistPosition)}
                        </span>
                        {booking.status !== 'checked_in' && booking.status !== 'cancelled' && (
                          <Button
                            variant="secondary"
                            onClick={() => handleCancel(booking.id)}
                            disabled={cancellingLoading || cancellingBookingId === booking.id}
                          >
                            {cancellingBookingId === booking.id ? 'Cancelling…' : 'Cancel'}
                          </Button>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {pastBookings.length > 0 && (
            <section className="mt-8">
              <h2 className="text-lg font-semibold text-text">Past & cancelled</h2>
              <ul className="mt-4 space-y-3" role="list">
                {pastBookings.map((booking) => (
                  <li key={booking.id} className="rounded-2xl border border-muted/15 bg-card shadow-[var(--shadow-card)] p-4 opacity-60">
                    <div className="flex items-start gap-4">
                      <DateBadge iso={booking.session.startsAt} accent={accentFor(booking.session.id)} />
                      <div className="min-w-0 flex-1">
                        <Link to={`/sessions/${booking.session.id}`} className="font-semibold text-text hover:text-primary">
                          {booking.session.title}
                        </Link>
                        <p className="mt-1 text-sm text-muted">{booking.session.location}</p>
                        <p className="text-sm text-text">{formatDateTime(booking.session.startsAt)} ({booking.session.durationMinutes} min)</p>
                      </div>
                      <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${getStatusColor(booking.status)}`}>
                        {getStatusLabel(booking.status)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}