import { Link } from 'react-router-dom'
import type { Session } from '../services/types'
import { accentFor } from '../lib/accent'
import { SeatDots } from './SeatDots'
import { ArrowRightIcon, ClockIcon, PinIcon } from './icons'

export interface SessionCardProps {
  session: Session
}

function timeOf(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

/** A session drawn as an admission ticket: coloured stub, perforation, details. */
export function SessionCard({ session }: SessionCardProps) {
  const accent = accentFor(session.id)
  const start = new Date(session.startsAt)
  const weekday = start.toLocaleString(undefined, { weekday: 'short' })
  const month = start.toLocaleString(undefined, { month: 'short' })

  return (
    <Link
      to={`/sessions/${session.id}`}
      className="group relative flex h-full overflow-hidden rounded-2xl border border-muted/15 bg-card shadow-[var(--shadow-card)] transition-all duration-200 hover:-translate-y-1 hover:rotate-[0.4deg] hover:shadow-[var(--shadow-lift)]"
    >
      <div
        className={`flex w-24 shrink-0 flex-col items-center justify-center gap-0.5 px-2 py-5 text-center ${accent.stub} ${accent.onStub}`}
      >
        <span className="text-[11px] font-bold uppercase tracking-[0.18em] opacity-90">
          {weekday}
        </span>
        <span aria-hidden="true" className="font-display text-5xl font-bold leading-none">
          {start.getDate()}
        </span>
        <span className="text-xs font-bold uppercase tracking-[0.18em]">{month}</span>
      </div>

      {/* Perforation: a dashed seam with a notch cut into the top and bottom edge. */}
      <div aria-hidden="true" className="relative w-0 border-l-2 border-dashed border-muted/25">
        <span className="absolute -left-2.5 -top-2.5 h-5 w-5 rounded-full border border-muted/15 bg-cream" />
        <span className="absolute -bottom-2.5 -left-2.5 h-5 w-5 rounded-full border border-muted/15 bg-cream" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col p-5">
        <h3 className="line-clamp-2 text-lg font-semibold leading-snug text-text">{session.title}</h3>
        <p className="mt-1 line-clamp-2 text-sm text-muted">{session.description}</p>

        <dl className="mt-4 space-y-1.5 text-sm">
          <div className="flex items-center gap-2">
            <dt className="sr-only">Starts</dt>
            <ClockIcon className={`h-4 w-4 shrink-0 ${accent.text}`} />
            <dd className="text-text">
              {weekday}, {month} {start.getDate()}, {timeOf(session.startsAt)}
              <span className="text-muted"> · {session.durationMinutes} min</span>
            </dd>
          </div>
          <div className="flex items-center gap-2">
            <dt className="sr-only">Location</dt>
            <PinIcon className={`h-4 w-4 shrink-0 ${accent.text}`} />
            <dd className="truncate text-text">{session.location}</dd>
          </div>
        </dl>

        <div className="mt-auto flex items-end justify-between gap-3 pt-5">
          <div>
            <SeatDots capacity={session.capacity} accent={accent} />
            <p className="mt-1.5 text-xs font-semibold text-muted">
              <span className="sr-only">Capacity: </span>
              {session.capacity} {session.capacity === 1 ? 'seat' : 'seats'}
            </p>
          </div>
          <span className={`inline-flex items-center gap-1 text-sm font-semibold ${accent.text}`}>
            View
            <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </div>
      </div>
    </Link>
  )
}
