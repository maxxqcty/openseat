import type { Accent } from '../lib/accent'

export interface DateBadgeProps {
  iso: string
  accent?: Accent
}

/** A calendar-leaf style badge: month on top, day number below. */
export function DateBadge({ iso, accent }: DateBadgeProps) {
  const date = new Date(iso)
  const month = date.toLocaleString(undefined, { month: 'short' })
  const day = date.getDate()
  const stub = accent ? `${accent.stub} ${accent.onStub}` : 'bg-primary text-surface'
  const body = accent ? `${accent.soft} ${accent.text}` : 'bg-primary/5 text-primary-dark'
  return (
    <div
      aria-hidden="true"
      className="flex h-14 w-14 shrink-0 flex-col items-center justify-center overflow-hidden rounded-xl border border-muted/15 text-center shadow-sm"
    >
      <span className={`w-full py-0.5 text-[10px] font-bold uppercase tracking-wider ${stub}`}>
        {month}
      </span>
      <span className={`flex-1 w-full font-display text-xl font-bold leading-7 ${body}`}>{day}</span>
    </div>
  )
}
