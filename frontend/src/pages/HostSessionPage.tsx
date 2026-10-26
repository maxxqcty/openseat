import { useParams } from 'react-router-dom'

export function HostSessionPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight text-text">Session roster</h1>
      <p className="mt-4 max-w-xl text-muted">
        The confirmed, waitlisted, and checked-in guests for session {id} will appear here once the
        roster API is connected.
      </p>
    </div>
  )
}
