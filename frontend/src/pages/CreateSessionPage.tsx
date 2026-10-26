import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, useCreateSession } from '../hooks'
import { Input } from '../components/Input'
import { Button } from '../components/Button'
import { ErrorState } from '../components/ErrorState'

export function CreateSessionPage() {
  const { user, loading: authLoading } = useAuth()
  const { create, error: createError } = useCreateSession()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [startsAt, setStartsAt] = useState('')
  const [durationMinutes, setDurationMinutes] = useState('90')
  const [capacity, setCapacity] = useState('10')
  const [location, setLocation] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      navigate(`/login?returnTo=${encodeURIComponent('/host/sessions/new')}`, { replace: true })
    }
  }, [user, authLoading, navigate])

  if (authLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-lg border border-muted/20 bg-surface p-8 text-center">
          <div className="inline-flex items-center gap-2 text-muted">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Loading…</span>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    setSubmitting(true)
    try {
      const session = await create({
        title: title.trim(),
        description: description.trim() || undefined,
        startsAt,
        durationMinutes: parseInt(durationMinutes, 10),
        capacity: parseInt(capacity, 10),
        location: location.trim(),
      })
      navigate(`/host/sessions/${session.id}`)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to create session')
    } finally {
      setSubmitting(false)
    }
  }

  // Default to tomorrow at 10:00 AM local time
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  tomorrow.setHours(10, 0, 0, 0)
  const defaultStartsAt = tomorrow.toISOString().slice(0, 16)

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight text-text">Create a session</h1>
      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        {(createError || formError) && (
          <ErrorState
            title="Could not create session"
            message={formError ?? createError ?? 'Unknown error'}
          />
        )}
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={120}
          autoFocus
        />
        <div className="space-y-1">
          <label htmlFor="description" className="block text-sm font-medium text-text">
            Description (optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={4}
            className="block w-full rounded-md border border-muted/30 bg-surface px-3 py-2 text-sm text-text placeholder:text-muted/70"
            placeholder="What will guests do in this session?"
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Start date & time"
            type="datetime-local"
            value={startsAt || defaultStartsAt}
            onChange={(e) => setStartsAt(e.target.value)}
            required
          />
          <Input
            label="Duration (minutes)"
            type="number"
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
            required
            min="15"
            max="480"
            step="15"
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Capacity"
            type="number"
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            required
            min="1"
            max="100"
          />
          <Input
            label="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            required
            minLength={3}
            maxLength={200}
          />
        </div>
        <div className="flex gap-4">
          <Button type="submit" disabled={submitting} className="flex-1">
            {submitting ? 'Creating…' : 'Create session'}
          </Button>
          <Button type="button" variant="secondary" onClick={() => navigate('/host')} className="flex-1">
            Cancel
          </Button>
        </div>
      </form>
    </div>
  )
}