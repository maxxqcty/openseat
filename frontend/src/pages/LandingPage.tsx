import { Link } from 'react-router-dom'
import { useSessions } from '../hooks'
import { Button } from '../components/Button'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { formatDateTime } from '../lib/date'

const steps = [
  {
    title: 'Publish a session',
    body: 'Set the time, place, and number of seats. No spreadsheets or group chats.',
  },
  {
    title: 'Take bookings',
    body: 'Guests reserve a seat, or join the waitlist when the session is full.',
  },
  {
    title: 'Fill every seat',
    body: 'Cancel a booking and the oldest waiting guest is promoted automatically.',
  },
]

export function LandingPage() {
  const { sessions, loading, error, reload } = useSessions()

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-muted/20 bg-surface p-6 animate-pulse">
              <div className="h-4 bg-muted/20 rounded w-3/4 mb-2" />
              <div className="h-4 bg-muted/20 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <ErrorState
          title="Could not load sessions"
          message={error}
          action={<Button onClick={reload} variant="secondary">Try again</Button>}
        />
      </div>
    )
  }

  return (
    <>
      <section className="bg-primary text-surface">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-[0.3em] uppercase">Workshop bookings</p>
          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-6xl">OpenSeat</h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed">
            Fill every seat, without overbooking. One roster, one waitlist, and automatic promotion
            when someone cancels.
          </p>
          <div className="mt-10 flex gap-4">
            <Link to="/signup" className="rounded-md bg-surface px-6 py-3 text-sm font-semibold text-primary hover:bg-surface/90">
              Create account
            </Link>
            <Link to="/login" className="rounded-md border-2 border-surface px-6 py-3 text-sm font-semibold hover:bg-surface/10">
              Sign in
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="grid gap-8 md:grid-cols-3">
          {steps.map((step, index) => (
            <article key={index} className="rounded-lg border border-muted/20 bg-surface p-6">
              <div className="text-3xl font-bold text-primary">{index + 1}</div>
              <h3 className="mt-4 text-lg font-semibold text-text">{step.title}</h3>
              <p className="mt-2 text-muted">{step.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold tracking-tight text-text">Upcoming sessions</h2>
          <Link to="/signup" className="hidden text-sm font-semibold text-primary hover:text-primary/80 sm:inline">
            Sign up to book
          </Link>
        </div>
        {sessions.length === 0 ? (
          <EmptyState
            title="No sessions yet"
            message="Check back soon or create your own session after signing in."
            action={<Link to="/signup" className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-surface hover:bg-primary/90">Create account</Link>}
          />
        ) : (
          <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="list">
            {sessions.map((session) => (
              <li key={session.id}>
                <Link
                  to={`/sessions/${session.id}`}
                  className="block rounded-lg border border-muted/20 bg-surface p-5 transition-shadow hover:shadow-md"
                >
                  <h3 className="text-lg font-semibold text-text line-clamp-1">{session.title}</h3>
                  <p className="mt-1 text-sm text-muted line-clamp-2">{session.description}</p>
                  <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                    <div>
                      <dt className="text-muted">Starts</dt>
                      <dd className="text-text">{formatDateTime(session.startsAt)}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Duration</dt>
                      <dd className="text-text">{session.durationMinutes} min</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Location</dt>
                      <dd className="text-text">{session.location}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Capacity</dt>
                      <dd className="text-text">{session.capacity}</dd>
                    </div>
                  </dl>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}