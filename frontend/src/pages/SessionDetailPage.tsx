import { useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useSessionDetail, useBooking, useCancelBooking, useAuth } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { formatDateTime } from '../lib/date'

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { session, loading, error, reload } = useSessionDetail(id!)
  const { book, loading: bookingLoading } = useBooking()
  const { cancelBooking, loading: cancellingLoading } = useCancelBooking()

  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [cancellingBookingId, setCancellingBookingId] = useState<string | null>(null)

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [message])

  async function handleBook() {
    if (!user) {
      window.location.href = `/login?returnTo=${encodeURIComponent(window.location.pathname)}`
      return
    }
    try {
      const booking = await book(id!)
      if (booking.status === 'confirmed') {
        setMessage({ type: 'success', text: 'Booking confirmed!' })
      } else {
        setMessage({ type: 'success', text: `Waitlisted, position ${booking.waitlistPosition}` })
      }
      reload()
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Booking failed' })
    }
  }

  async function handleCancel(bookingId: string) {
    setCancellingBookingId(bookingId)
    try {
      await cancelBooking(bookingId)
      setMessage({ type: 'success', text: 'Booking cancelled' })
      reload()
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Cancellation failed' })
    } finally {
      setCancellingBookingId(null)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="space-y-4 animate-pulse">
          <div className="h-8 bg-muted/20 rounded w-1/3" />
          <div className="h-4 bg-muted/20 rounded w-full" />
          <div className="h-4 bg-muted/20 rounded w-1/2" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-20 bg-muted/20 rounded" />
            <div className="h-20 bg-muted/20 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState
          title="Could not load session"
          message={error}
          action={<Button onClick={reload} variant="secondary">Try again</Button>}
        />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState title="Session not found" message="This session no longer exists." />
      </div>
    )
  }

  const seatsLeft = Math.max(0, session.capacity - session.confirmedCount - session.checkedInCount)
  const isBookable = session.status === 'scheduled' && !session.past && seatsLeft > 0
  const isWaitlistable = session.status === 'scheduled' && !session.past
  const canBook = user && isBookable
  const canWaitlist = user && isWaitlistable
  const isBookingPending = bookingLoading || cancellingLoading

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-text">{session.title}</h1>
        <p className="mt-2 text-muted">{session.description}</p>
      </header>

      {message && (
        <div
          className={`mb-6 rounded-md p-4 text-sm ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}
          role="alert"
        >
          {message.text}
        </div>
      )}

      <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 text-sm mb-6">
        <div>
          <dt className="text-muted">Date & time</dt>
          <dd className="text-text">{formatDateTime(session.startsAt)} ({session.durationMinutes} min)</dd>
        </div>
        <div>
          <dt className="text-muted">Location</dt>
          <dd className="text-text">{session.location}</dd>
        </div>
        <div>
          <dt className="text-muted">Seats left</dt>
          <dd className="text-text font-semibold">{seatsLeft} / {session.capacity}</dd>
        </div>
        <div>
          <dt className="text-muted">Status</dt>
          <dd className="text-text capitalize">{session.status}</dd>
        </div>
      </dl>

      {user && session.myBooking && (
        <section className="mb-6 rounded-lg border border-muted/20 bg-surface p-4">
          <h2 className="text-lg font-semibold text-text">Your booking</h2>
          <p className="mt-1 capitalize text-text">
            Status: <span className="font-medium">
              {session.myBooking.status === 'confirmed' ? 'Confirmed' :
               session.myBooking.status === 'waitlisted' ? `Waitlisted, position ${session.myBooking.waitlistPosition}` :
               session.myBooking.status === 'checked_in' ? 'Checked in' : 'Cancelled'}
            </span>
          </p>
          {session.myBooking.status !== 'cancelled' && session.myBooking.status !== 'checked_in' && (
            <Button
              variant="danger"
              className="mt-4"
              onClick={() => handleCancel(session.myBooking!.id)}
              disabled={isBookingPending || cancellingBookingId === session.myBooking.id}
            >
              {cancellingBookingId === session.myBooking.id ? 'Cancelling…' : 'Cancel booking'}
            </Button>
          )}
        </section>
      )}

      {user && !session.myBooking && (canBook || canWaitlist) && (
        <section className="mb-6">
          <Button
            className="w-full"
            onClick={handleBook}
            disabled={isBookingPending || (!canBook && !canWaitlist)}
          >
            {bookingLoading ? 'Booking…' : seatsLeft > 0 ? 'Book seat' : 'Join waitlist'}
          </Button>
        </section>
      )}

      {user && !session.myBooking && !canBook && !canWaitlist && (
        <EmptyState
          title="Booking not available"
          message={session.past ? 'This session has already ended.' : session.status === 'cancelled' ? 'This session has been cancelled.' : 'No seats or waitlist available.'}
        />
      )}

      {!user && (
        <section className="mb-6 text-center">
          <p className="text-muted">
            <Link to={`/login?returnTo=${encodeURIComponent(window.location.pathname)}`} className="font-semibold text-primary hover:text-primary/80">Sign in</Link>{' '}
            or{' '}
            <Link to={`/signup?returnTo=${encodeURIComponent(window.location.pathname)}`} className="font-semibold text-primary hover:text-primary/80">create an account</Link>{' '}
            to book a seat.
          </p>
        </section>
      )}

      <section>
        <h2 className="text-lg font-semibold text-text mb-4">Details</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <dt className="text-muted">Host</dt>
            <dd className="text-text">{session.hostId}</dd>
          </div>
          <div>
            <dt className="text-muted">Created</dt>
            <dd className="text-text">{new Date(session.createdAt).toLocaleString()}</dd>
          </div>
        </dl>
      </section>
    </div>
  )
}