import type { Accent } from '../lib/accent'

export interface SeatDotsProps {
  capacity: number
  /** Seats already taken (confirmed plus checked in). */
  taken?: number
  accent: Accent
  /** Cap the number of dots drawn; the rest collapse into "+N". */
  max?: number
  className?: string
}

/** One small chair-shaped tile per seat: filled when taken, outlined when open. */
export function SeatDots({ capacity, taken = 0, accent, max = 20, className = '' }: SeatDotsProps) {
  const shown = Math.min(capacity, max)
  const extra = capacity - shown
  return (
    <div className={`flex flex-wrap items-center gap-1 ${className}`.trim()} aria-hidden="true">
      {Array.from({ length: shown }).map((_, index) => (
        <span
          key={index}
          className={`h-3 w-3 rounded-[4px] ${
            index < taken ? accent.dot : `${accent.dot} opacity-25`
          }`}
        />
      ))}
      {extra > 0 && <span className="ml-1 text-[11px] font-semibold text-muted">+{extra}</span>}
    </div>
  )
}
