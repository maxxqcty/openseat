const statusLabels = {
  confirmed: 'Confirmed',
  waitlisted: 'Waitlisted',
  checked_in: 'Checked in',
  cancelled: 'Cancelled',
} as const

const statusClasses = {
  confirmed: 'bg-success/5 text-success',
  waitlisted: 'bg-primary/10 text-primary',
  checked_in: 'bg-muted/10 text-text',
  cancelled: 'bg-danger/10 text-danger',
} as const

export type BookingStatus = keyof typeof statusLabels

export interface StatusBadgeProps {
  status: BookingStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold ${statusClasses[status]}`}
    >
      {statusLabels[status]}
    </span>
  )
}
