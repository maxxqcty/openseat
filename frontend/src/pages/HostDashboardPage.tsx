import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, useHostSessions, useCancelSession } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { formatDateTime } from '../lib/date'

export function HostDashboardPage() {
  const { user, loading: authLoading } = useAuth()
  const { sessions, error, reload } = useHostSessions()
  const { cancel, loading: cancellingLoading } = useCancelSession()
  const navigate = useNavigate()
  const [cancellingSessionId, setCancellingSessionId] = useState<string | null>(null)
  const [showConfirm, setShowConfirm] = useState<string | null>(null)

  const [now] = useState(() => Date.now())
  const upcoming = useMemo(() => sessions.filter((s) => s.status === 'scheduled' && Date.parse(s.startsAt) > now), [sessions, now])
  const past = useMemo(() => sessions.filter((s) => s.status === 'cancelled' || Date.parse(s.startsAt) <= now), [sessions, now])

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      navigate(`/login?returnTo=${encodeURIComponent('/host')}`, { replace: true })
    }
  }, [user, authLoading, navigate])

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

  async function handleCancel(sessionId: string) {
    setCancellingSessionId(sessionId)
    setShowConfirm(sessionId)
  }

  async function confirmCancel(sessionId: string) {
    try {
      await cancel(sessionId)
      reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to cancel session')
    } finally {
      setShowConfirm(null)
      setCancellingSessionId(null)
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState
          title="Could not load sessions"
          message={error}
          action={<Button onClick={reload} variant="secondary">Try again</Button>}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-text">Host dashboard</h1>
        <Link to="/host/sessions/new" className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-surface hover:bg-primary/90">
          Create session
        </Link>
      </div>

      {sessions.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          message="Create your first session to start accepting bookings."
          action={<Link to="/host/sessions/new" className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-surface hover:bg-primary/90">Create session</Link>}
        />
      ) : (
        <>
          {upcoming.length > 0 && (
            <section className="mt-8">
              <h2 className="text-lg font-semibold text-text">Upcoming</h2>
              <ul className="mt-4 space-y-3" role="list">
                {upcoming.map((session) => (
                  <li key={session.id} className="rounded-lg border border-muted/20 bg-surface p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <Link to={`/host/sessions/${session.id}`} className="font-semibold text-text hover:text-primary truncate block">
                          {session.title}
                        </Link>
                        <p className="mt-1 text-sm text-muted">{session.location}</p>
                        <p className="text-sm text-text">{formatDateTime(session.startsAt)} ({session.durationMinutes} min)</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-50 text-green-700">
                          {session.capacity} seats
                        </span>
                        <Button
                          variant="secondary"
                          onClick={() => handleCancel(session.id)}
                          disabled={cancellingLoading || cancellingSessionId === session.id}
                        >
                          {cancellingSessionId === session.id ? 'Cancelling…' : 'Cancel'}
                        </Button>
                      </div>
                    </div>
                    {showConfirm === session.id && (
                      <div className="mt-4 flex items-center gap-2 text-sm text-danger">
                        <p>This will cancel the session and all bookings. Are you sure?</p>
                        <Button variant="danger" onClick={() => confirmCancel(session.id)}>Yes, cancel</Button>
                        <Button variant="secondary" onClick={() => setShowConfirm(null)}>No</Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {past.length > 0 && (
            <section className="mt-8">
              <h2 className="text-lg font-semibold text-text">Past & cancelled</h2>
              <ul className="mt-4 space-y-3" role="list">
                {past.map((session) => (
                  <li key={session.id} className="rounded-lg border border-muted/20 bg-surface p-4 opacity-60">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <Link to={`/host/sessions/${session.id}`} className="font-semibold text-text hover:text-primary truncate block">
                          {session.title}
                        </Link>
                        <p className="mt-1 text-sm text-muted">{session.location}</p>
                        <p className="text-sm text-text">{formatDateTime(session.startsAt)} ({session.durationMinutes} min)</p>
                      </div>
                      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-muted/20 text-muted">
                        {session.status}
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