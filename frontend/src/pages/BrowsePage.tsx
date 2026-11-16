import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth, useSessions } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { SessionCard } from '../components/SessionCard'

/** The signed-in home: find a workshop and open it to book a seat. */
export function BrowsePage() {
  const { user } = useAuth()
  const { sessions, loading, error, reload } = useSessions()
  const [query, setQuery] = useState('')

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return sessions
    return sessions.filter((session) =>
      [session.title, session.description, session.location].some((field) =>
        field.toLowerCase().includes(needle),
      ),
    )
  }, [sessions, query])

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-text">Find a workshop</h1>
          <p className="mt-2 text-muted">
            Pick a session, then book a seat or join the waitlist.
          </p>
        </div>
        {user ? (
          <Link
            to="/host/sessions/new"
            className="inline-flex items-center justify-center rounded-lg border border-muted/25 bg-card px-4 py-2 text-sm font-semibold text-text shadow-sm transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            + Host a session
          </Link>
        ) : (
          <p className="text-sm text-muted">
            <Link to="/login?returnTo=%2Fsessions" className="font-semibold text-primary hover:text-primary-dark">
              Sign in
            </Link>{' '}
            or{' '}
            <Link to="/signup?returnTo=%2Fsessions" className="font-semibold text-primary hover:text-primary-dark">
              create an account
            </Link>{' '}
            to book.
          </p>
        )}
      </header>

      {!loading && !error && sessions.length > 0 && (
        <div className="mt-6">
          <label htmlFor="session-search" className="sr-only">
            Search sessions
          </label>
          <input
            id="session-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by title, place or topic"
            className="block w-full max-w-md rounded-lg border border-muted/25 bg-card px-3.5 py-2.5 text-sm text-text shadow-sm transition-colors placeholder:text-muted/70 hover:border-muted/40 focus:border-primary"
          />
        </div>
      )}

      {loading ? (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-52 animate-pulse rounded-2xl border border-muted/15 bg-card shadow-[var(--shadow-card)]"
            />
          ))}
        </div>
      ) : error ? (
        <div className="mt-8">
          <ErrorState
            title="Could not load sessions"
            message={error}
            action={<Button onClick={reload} variant="secondary">Try again</Button>}
          />
        </div>
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          message="Nothing is scheduled right now. Check back soon, or host the first one."
          action={
            <Link
              to="/host/sessions/new"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-surface shadow-sm hover:bg-primary-dark"
            >
              Host a session
            </Link>
          }
        />
      ) : results.length === 0 ? (
        <EmptyState
          title="No matches"
          message={`Nothing matches "${query.trim()}". Try a different word.`}
          action={<Button variant="secondary" onClick={() => setQuery('')}>Clear search</Button>}
        />
      ) : (
        <>
          <p className="mt-6 text-sm text-muted" aria-live="polite">
            {results.length} {results.length === 1 ? 'session' : 'sessions'}
          </p>
          <ul className="mt-3 grid gap-5 sm:grid-cols-2 lg:grid-cols-3" role="list">
            {results.map((session) => (
              <li key={session.id}>
                <SessionCard session={session} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
