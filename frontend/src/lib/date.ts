/**
 * Format a Date for an `<input type="datetime-local">`.
 *
 * That input carries wall-clock time in the browser's zone, so it must not be
 * converted to UTC — `toISOString().slice(0, 16)` would shift the value by the
 * local offset.
 */
export function toDateTimeInputValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return `${day}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatTimeRange(startsAt: string, durationMinutes: number): string {
  const start = new Date(startsAt)
  const end = new Date(start.getTime() + durationMinutes * 60 * 1000)
  return `${start.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })} – ${end.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
}

const CHECK_IN_OPENS_BEFORE_START_MS = 2 * 60 * 60 * 1000

/** When a session ends (start plus duration), as epoch milliseconds. */
export function sessionEndsAt(startsAt: string, durationMinutes: number): number {
  return Date.parse(startsAt) + durationMinutes * 60 * 1000
}

/** A session has ended once start plus duration has passed (matches the API's `past`). */
export function hasSessionEnded(startsAt: string, durationMinutes: number, now: number): boolean {
  return now > sessionEndsAt(startsAt, durationMinutes)
}

/** Check-in is open from two hours before the start until the session ends. */
export function isCheckInWindowOpen(
  startsAt: string,
  durationMinutes: number,
  now: number,
): boolean {
  return (
    now >= Date.parse(startsAt) - CHECK_IN_OPENS_BEFORE_START_MS &&
    now <= sessionEndsAt(startsAt, durationMinutes)
  )
}
