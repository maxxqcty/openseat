import { useParams } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth, useSessionDetail, useRoster, useCheckIn } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { formatDateTime } from '../lib/date'

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
    case 'confirmed': return 'bg-green-50 text-green-700'
    case 'waitlisted': return 'bg-amber-50 text-amber-700'
    case 'checked_in': return 'bg-blue-50 text-blue-700'
    case 'cancelled': return 'bg-muted/20 text-muted'
    default: return 'bg-surface text-text'
  }
}

export function HostSessionPage() {
  const { id } = useParams<{ id: string }>()
  const { user, loading: authLoading } = useAuth()
  const { session, loading: sessionLoading, error: sessionError, reload } = useSessionDetail(id!)
  const { roster, loading: rosterLoading, error: rosterError, reload: reloadRoster } = useRoster(id!)
  const { checkIn, loading: checkInLoading } = useCheckIn()

  const [checkInError, setCheckInError] = useState<string | null>(null)
  const [checkingInId, setCheckingInId] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      window.location.href = `/login?returnTo=${encodeURIComponent(window.location.pathname)}`
    }
  }, [user, authLoading])

  if (authLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-lg border border-muted/20 bg-surface p-8 text-center">
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

  if (sessionLoading || rosterLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="space-y-4 animate-pulse">
          <div className="h-8 bg-muted/20 rounded w-1/3" />
          <div className="h-4 bg-muted/20 rounded w-full" />
          <div className="grid gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 bg-muted/20 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (sessionError || rosterError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState
          title="Could not load roster"
          message={sessionError ?? rosterError ?? 'Unknown error'}
          action={<Button onClick={() => { reload(); reloadRoster(); }} variant="secondary">Try again</Button>}
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

  async function handleCheckIn(bookingId: string) {
    setCheckingInId(bookingId)
    setCheckInError(null)
    try {
      await checkIn(bookingId)
      reloadRoster()
      reload()
    } catch (err) {
      setCheckInError(err instanceof Error ? err.message : 'Check-in failed')
    } finally {
      setCheckingInId(null)
    }
  }

  const confirmed = roster.filter((r) => r.status === 'confirmed')
  const waitlisted = roster.filter((r) => r.status === 'waitlisted')
  const checkedIn = roster.filter((r) => r.status === 'checked_in')

  const canCheckIn = session.status === 'scheduled' && !session.past

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">{session.title}</h1>
          <p className="mt-1 text-muted">{session.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/host" className="rounded-md border border-muted/30 px-3 py-2 text-sm font-medium text-muted hover:bg-muted/10 hover:text-text">
            ← Back
          </Link>
        </div>
      </header>

      {checkInError && (
        <div className="mb-6 rounded-md bg-red-50 p-4 text-sm text-red-800" role="alert">
          {checkInError}
        </div>
      )}

      <dl className="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-4 text-sm mb-6">
        <div>
          <dt className="text-muted">Date & time</dt>
          <dd className="text-text">{formatDateTime(session.startsAt)} ({session.durationMinutes} min)</dd>
        </div>
        <div>
          <dt className="text-muted">Location</dt>
          <dd className="text-text">{session.location}</dd>
        </div>
        <div>
          <dt className="text-muted">Seats</dt>
          <dd className="text-text font-semibold">
            {session.confirmedCount + session.checkedInCount} / {session.capacity} filled
            ({session.waitlistCount} waiting)
          </dd>
        </div>
      </dl>

      <section className="mb-8">
        <h2 className="text-lg font-semibold text-text mb-4">Confirmed ({confirmed.length})</h2>
        {confirmed.length === 0 ? (
          <EmptyState title="No confirmed guests" message="Guests who book when seats are available appear here." />
        ) : (
          <ul className="space-y-2" role="list">
            {confirmed.map((entry) => (
              <li key={entry.bookingId} className="flex items-center justify-between rounded-lg border border-muted/20 bg-surface p-3">
                <span className="font-medium text-text">{entry.displayName}</span>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(entry.status)}`}>
                    {getStatusLabel(entry.status, entry.waitlistPosition)}
                  </span>
                  {canCheckIn && entry.status === 'confirmed' && (
                    <Button
                      onClick={() => handleCheckIn(entry.bookingId)}
                      disabled={checkInLoading || checkingInId === entry.bookingId}
                    >
                      {checkingInId === entry.bookingId ? 'Checking in…' : 'Check in'}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-8">
        <h2 className="text-lg font-semibold text-text mb-4">Waitlisted ({waitlisted.length})</h2>
        {waitlisted.length === 0 ? (
          <EmptyState title="No waitlisted guests" message="Guests who join when the session is full appear here in order." />
        ) : (
          <ul className="space-y-2" role="list">
            {waitlisted.map((entry) => (
              <li key={entry.bookingId} className="flex items-center justify-between rounded-lg border border-muted/20 bg-surface p-3">
                <span className="font-medium text-text">{entry.displayName}</span>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(entry.status)}`}>
                  {getStatusLabel(entry.status, entry.waitlistPosition)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-text mb-4">Checked in ({checkedIn.length})</h2>
        {checkedIn.length === 0 ? (
          <EmptyState title="No guests checked in yet" message="Checked-in guests appear here during the session." />
        ) : (
          <ul className="space-y-2" role="list">
            {checkedIn.map((entry) => (
              <li key={entry.bookingId} className="flex items-center justify-between rounded-lg border border-muted/20 bg-surface p-3">
                <span className="font-medium text-text">{entry.displayName}</span>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(entry.status)}`}>
                  {getStatusLabel(entry.status)}
                  {entry.checkedInAt && (
                    <span className="ml-2 text-xs text-muted">
                      at {new Date(entry.checkedInAt).toLocaleTimeString()}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}