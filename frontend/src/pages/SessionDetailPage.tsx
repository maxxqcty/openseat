import { Link, useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useSessionDetail, useBooking, useCancelBooking, useAuth } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { SeatDots } from '../components/SeatDots'
import { StatusBadge } from '../components/StatusBadge'
import { CalendarIcon, ClockIcon, PinIcon, UsersIcon } from '../components/icons'
import { accentFor } from '../lib/accent'
import { formatDateTime } from '../lib/date'

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
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
      navigate(`/login?returnTo=${encodeURIComponent(`/sessions/${id ?? ''}`)}`)
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
      <div className="mx-auto max-w-5xl px-4 py-12">
        <div className="animate-pulse space-y-4">
          <div className="h-40 rounded-3xl bg-muted/15" />
          <div className="grid gap-4 md:grid-cols-[1fr_340px]">
            <div className="h-56 rounded-2xl bg-muted/15" />
            <div className="h-56 rounded-2xl bg-muted/15" />
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

  const accent = accentFor(session.id)
  const taken = session.confirmedCount + session.checkedInCount
  const seatsLeft = Math.max(0, session.capacity - taken)
  const isBookable = session.status === 'scheduled' && !session.past && seatsLeft > 0
  const isWaitlistable = session.status === 'scheduled' && !session.past
  const canBook = user && isBookable
  const canWaitlist = user && isWaitlistable
  const isBookingPending = bookingLoading || cancellingLoading
  const start = new Date(session.startsAt)
  const returnTo = encodeURIComponent(`/sessions/${session.id}`)
  const full = seatsLeft === 0

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <Link
        to="/sessions"
        className="mb-5 inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-text"
      >
        ← All sessions
      </Link>

      <header
        className={`relative overflow-hidden rounded-3xl ${accent.stub} ${accent.onStub} shadow-[var(--shadow-lift)]`}
      >
        <div aria-hidden="true" className="bg-dotgrid pointer-events-none absolute inset-0 opacity-15" />
        <div className="relative flex flex-col gap-6 p-7 sm:flex-row sm:items-center sm:p-9">
          <div
            aria-hidden="true"
            className="flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-2xl bg-white/20 text-center backdrop-blur-sm"
          >
            <span className="text-xs font-bold uppercase tracking-[0.2em]">
              {start.toLocaleString(undefined, { weekday: 'short' })}
            </span>
            <span className="font-display text-5xl font-bold leading-none">{start.getDate()}</span>
            <span className="text-xs font-bold uppercase tracking-[0.2em]">
              {start.toLocaleString(undefined, { month: 'short' })}
            </span>
          </div>
          <div className="min-w-0">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{session.title}</h1>
            <p className="mt-2 max-w-2xl opacity-90">{session.description}</p>
            <div className="mt-4 flex flex-wrap gap-2 text-sm font-semibold">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-black/15 px-3 py-1">
                <ClockIcon className="h-4 w-4" />
                {formatDateTime(session.startsAt)} ({session.durationMinutes} min)
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-black/15 px-3 py-1">
                <PinIcon className="h-4 w-4" />
                {session.location}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="mt-6 grid items-start gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-muted/15 bg-card p-6 shadow-[var(--shadow-card)]">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-text">The room</h2>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${accent.soft} ${accent.text}`}>
                {session.capacity} {session.capacity === 1 ? 'seat' : 'seats'}
              </span>
            </div>
            <SeatDots
              capacity={session.capacity}
              taken={taken}
              accent={accent}
              max={60}
              className="mt-4 gap-1.5 [&>span]:h-5 [&>span]:w-5 [&>span]:rounded-md"
            />
            <dl className="mt-5 grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl bg-cream px-3 py-3">
                <dt className="text-xs font-semibold text-muted">Confirmed</dt>
                <dd className="font-display text-2xl font-bold text-text">{session.confirmedCount}</dd>
              </div>
              <div className="rounded-xl bg-cream px-3 py-3">
                <dt className="text-xs font-semibold text-muted">Checked in</dt>
                <dd className="font-display text-2xl font-bold text-text">{session.checkedInCount}</dd>
              </div>
              <div className="rounded-xl bg-emerald-50 px-3 py-3">
                <dt className="text-xs font-semibold text-emerald-800">Waitlisted</dt>
                <dd className="font-display text-2xl font-bold text-emerald-900">{session.waitlistCount}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-2xl border border-muted/15 bg-card p-6 shadow-[var(--shadow-card)]">
            <h2 className="text-xl font-bold text-text">Details</h2>
            <dl className="mt-4 grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
              <div className="flex items-start gap-3">
                <CalendarIcon className={`mt-0.5 h-5 w-5 ${accent.text}`} />
                <div>
                  <dt className="text-muted">Created</dt>
                  <dd className="text-text">{new Date(session.createdAt).toLocaleString()}</dd>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <UsersIcon className={`mt-0.5 h-5 w-5 ${accent.text}`} />
                <div>
                  <dt className="text-muted">Host</dt>
                  <dd className="font-mono text-xs text-text">{session.hostId.slice(0, 8)}</dd>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <ClockIcon className={`mt-0.5 h-5 w-5 ${accent.text}`} />
                <div>
                  <dt className="text-muted">Status</dt>
                  <dd className="capitalize text-text">{session.past ? 'ended' : session.status}</dd>
                </div>
              </div>
            </dl>
          </section>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-24">
          <section className="overflow-hidden rounded-2xl border border-muted/15 bg-card shadow-[var(--shadow-lift)]">
            <div className={`${accent.soft} px-6 py-5`}>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-muted">Seats left</p>
              <p className="mt-1 flex items-baseline gap-2">
                <span className={`font-display text-5xl font-bold ${accent.text}`}>{seatsLeft}</span>
                <span className="text-lg font-semibold text-muted">/ {session.capacity}</span>
              </p>
              <p className="mt-1 text-sm text-muted">
                {session.status === 'cancelled'
                  ? 'This session was cancelled.'
                  : session.past
                    ? 'This session has ended.'
                    : full
                      ? 'Full. Join the waitlist and get promoted if a seat opens.'
                      : seatsLeft <= 2
                        ? 'Almost full. Grab a seat while you can.'
                        : 'Plenty of room.'}
              </p>
            </div>

            <div className="space-y-4 p-6">
              {message && (
                <div
                  className={`rounded-lg p-3 text-sm font-medium ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}
                  role="alert"
                >
                  {message.text}
                </div>
              )}

              {user && session.myBooking && (
                <div>
                  <h2 className="text-sm font-bold text-text">Your booking</h2>
                  <p className="mt-2 flex flex-wrap items-center gap-2 text-text">
                    <StatusBadge status={session.myBooking.status} />
                    {session.myBooking.status === 'waitlisted' && (
                      <span className="text-sm font-semibold text-primary">
                        Position {session.myBooking.waitlistPosition}
                      </span>
                    )}
                  </p>
                  <p className="sr-only">
                    Status:{' '}
                    {session.myBooking.status === 'confirmed'
                      ? 'Confirmed'
                      : session.myBooking.status === 'waitlisted'
                        ? `Waitlisted, position ${session.myBooking.waitlistPosition}`
                        : session.myBooking.status === 'checked_in'
                          ? 'Checked in'
                          : 'Cancelled'}
                  </p>
                  {session.myBooking.status !== 'cancelled' &&
                    session.myBooking.status !== 'checked_in' && (
                      <Button
                        variant="danger"
                        className="mt-4 w-full"
                        onClick={() => handleCancel(session.myBooking!.id)}
                        disabled={isBookingPending || cancellingBookingId === session.myBooking.id}
                      >
                        {cancellingBookingId === session.myBooking.id ? 'Cancelling…' : 'Cancel booking'}
                      </Button>
                    )}
                </div>
              )}

              {user && !session.myBooking && (canBook || canWaitlist) && (
                <Button
                  className="w-full py-3 text-base"
                  onClick={handleBook}
                  disabled={isBookingPending || (!canBook && !canWaitlist)}
                >
                  {bookingLoading ? 'Booking…' : seatsLeft > 0 ? 'Book seat' : 'Join waitlist'}
                </Button>
              )}

              {user && !session.myBooking && !canBook && !canWaitlist && (
                <EmptyState
                  title="Booking not available"
                  message={
                    session.past
                      ? 'This session has already ended.'
                      : session.status === 'cancelled'
                        ? 'This session has been cancelled.'
                        : 'No seats or waitlist available.'
                  }
                />
              )}

              {!user && (
                <p className="text-sm text-muted">
                  <Link
                    to={`/login?returnTo=${returnTo}`}
                    className="font-semibold text-primary hover:text-primary-dark"
                  >
                    Sign in
                  </Link>{' '}
                  or{' '}
                  <Link
                    to={`/signup?returnTo=${returnTo}`}
                    className="font-semibold text-primary hover:text-primary-dark"
                  >
                    create an account
                  </Link>{' '}
                  to book a seat.
                </p>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
