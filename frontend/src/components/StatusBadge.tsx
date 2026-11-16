const statusLabels = {
  confirmed: 'Confirmed',
  waitlisted: 'Waitlisted',
  checked_in: 'Checked in',
  cancelled: 'Cancelled',
} as const

const statusClasses = {
  confirmed: 'bg-success/10 text-success ring-success/20',
  waitlisted: 'bg-muted/10 text-text ring-muted/25',
  checked_in: 'bg-primary-dark text-white ring-primary-dark',
  cancelled: 'bg-danger/10 text-danger ring-danger/20',
} as const

const dotClasses = {
  confirmed: 'bg-success',
  waitlisted: 'bg-muted',
  checked_in: 'bg-emerald-300',
  cancelled: 'bg-danger',
} as const

export type BookingStatus = keyof typeof statusLabels

export interface StatusBadgeProps {
  status: BookingStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusClasses[status]}`}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${dotClasses[status]}`} />
      {statusLabels[status]}
    </span>
  )
}
