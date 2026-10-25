import { useParams } from 'react-router-dom'

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight text-text">Session details</h1>
      <p className="mt-4 max-w-xl text-muted">
        Details for session {id} will appear here once the sessions API is connected.
      </p>
    </div>
  )
}
