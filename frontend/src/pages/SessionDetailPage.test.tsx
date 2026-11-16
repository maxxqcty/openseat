import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { mockApi, resetMock } from '../services/mock'
import { ApiError } from '../services/types'
import type { Booking, SessionDetail } from '../services/types'

const POLL_MS = 10_000

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

async function signInAs(email: string) {
  await mockApi.auth.login(email, 'password123')
}

/** Seed: [0] has two free seats, [1] ("Sold Out Bookbinding") is full. */
async function seededSessions() {
  const [open, full] = await mockApi.sessions.list()
  return { open, full }
}

function booking(overrides: Partial<Booking>): Booking {
  return {
    id: 'b-test',
    sessionId: 's-test',
    userId: 'u-test',
    status: 'confirmed',
    createdAt: new Date().toISOString(),
    ...overrides,
  }
}

beforeEach(() => {
  resetMock()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('booking from the session detail page', () => {
  it('books a free seat and shows the confirmed booking', async () => {
    await signInAs('host@example.com')
    const { open } = await seededSessions()
    renderAt(`/sessions/${open.id}`)

    fireEvent.click(await screen.findByRole('button', { name: 'Book seat' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Booking confirmed!')
    expect(await screen.findByRole('heading', { name: 'Your booking' })).toBeInTheDocument()
    expect(screen.getByText('Status: Confirmed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Book seat' })).not.toBeInTheDocument()
  })

  it('shows seats left and offers the waitlist when the session is full', async () => {
    await signInAs('host@example.com')
    const { full } = await seededSessions()
    renderAt(`/sessions/${full.id}`)

    expect(await screen.findByText('Seats left')).toBeInTheDocument()
    expect(screen.getByText('/ 1')).toBeInTheDocument()
    expect(screen.getByText(/Full\. Join the waitlist/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Join waitlist' })).toBeEnabled()
  })

  it('renders the waitlist position after joining the waitlist', async () => {
    await signInAs('host@example.com')
    const { full } = await seededSessions()
    renderAt(`/sessions/${full.id}`)

    fireEvent.click(await screen.findByRole('button', { name: 'Join waitlist' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Waitlisted, position 1')
    expect(await screen.findByText('Position 1')).toBeInTheDocument()
    expect(screen.getByText('Status: Waitlisted, position 1')).toBeInTheDocument()
  })

  it('disables the button while the request is pending and sends it only once', async () => {
    await signInAs('host@example.com')
    const { open } = await seededSessions()
    let finish!: (value: Booking) => void
    const book = vi.spyOn(mockApi.sessions, 'book').mockReturnValue(
      new Promise<Booking>((resolve) => {
        finish = resolve
      }),
    )
    renderAt(`/sessions/${open.id}`)

    fireEvent.click(await screen.findByRole('button', { name: 'Book seat' }))

    const pending = await screen.findByRole('button', { name: 'Booking…' })
    expect(pending).toBeDisabled()
    fireEvent.click(pending)
    expect(book).toHaveBeenCalledTimes(1)

    await act(async () => {
      finish(booking({ sessionId: open.id, status: 'confirmed' }))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('Booking confirmed!')
  })

  it('shows the server message on a 409 conflict and keeps the page usable', async () => {
    await signInAs('host@example.com')
    const { open } = await seededSessions()
    vi.spyOn(mockApi.sessions, 'book').mockRejectedValue(
      new ApiError('booking_conflict', 'You already have an active booking for this session'),
    )
    renderAt(`/sessions/${open.id}`)

    fireEvent.click(await screen.findByRole('button', { name: 'Book seat' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You already have an active booking for this session',
    )
    expect(screen.getByRole('button', { name: 'Book seat' })).toBeEnabled()
  })

  it('shows an actionable message on a 403', async () => {
    await signInAs('host@example.com')
    const { open } = await seededSessions()
    vi.spyOn(mockApi.sessions, 'book').mockRejectedValue(
      new ApiError('forbidden', 'You do not have permission to do that.'),
    )
    renderAt(`/sessions/${open.id}`)

    fireEvent.click(await screen.findByRole('button', { name: 'Book seat' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You do not have permission to do that.',
    )
  })
})

describe('an expired session (401)', () => {
  it('sends the guest to sign in and returns to the same session afterwards', async () => {
    await signInAs('host@example.com')
    const { open } = await seededSessions()
    vi.spyOn(mockApi.sessions, 'book').mockRejectedValueOnce(
      new ApiError('unauthorized', 'Sign in required'),
    )
    renderAt(`/sessions/${open.id}`)

    fireEvent.click(await screen.findByRole('button', { name: 'Book seat' }))

    const dialog = await screen.findByRole('dialog', { name: 'Sign in' })
    expect(screen.queryByRole('heading', { level: 1, name: open.title })).not.toBeInTheDocument()

    fireEvent.change(within(dialog).getByLabelText('Email'), {
      target: { value: 'host@example.com' },
    })
    fireEvent.change(within(dialog).getByLabelText('Password'), {
      target: { value: 'password123' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: open.title }),
    ).toBeInTheDocument()
  })
})

describe('polling the session detail', () => {
  async function renderWaitlisted() {
    await signInAs('host@example.com')
    const { full } = await seededSessions()
    const base: SessionDetail = await mockApi.sessions.get(full.id)
    const waitlisted: SessionDetail = {
      ...base,
      myBooking: booking({
        sessionId: full.id,
        status: 'waitlisted',
        waitlistPosition: 1,
      }),
    }
    const promoted: SessionDetail = {
      ...base,
      myBooking: booking({ sessionId: full.id, status: 'confirmed' }),
    }
    const get = vi
      .spyOn(mockApi.sessions, 'get')
      .mockResolvedValueOnce(waitlisted)
      .mockResolvedValue(promoted)

    // Fake only the interval so findBy* and waitFor keep using real timers.
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const view = renderAt(`/sessions/${full.id}`)
    expect(await screen.findByText('Status: Waitlisted, position 1')).toBeInTheDocument()
    return { get, view }
  }

  async function advance(ms: number) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ms)
    })
  }

  it('shows Confirmed within one interval after the waiter is promoted', async () => {
    const { get } = await renderWaitlisted()
    expect(get).toHaveBeenCalledTimes(1)

    await advance(POLL_MS)

    expect(get).toHaveBeenCalledTimes(2)
    expect(await screen.findByText('Status: Confirmed')).toBeInTheDocument()
    expect(screen.queryByText(/Waitlisted, position/)).not.toBeInTheDocument()
  })

  it('does not poll before the interval has elapsed', async () => {
    const { get } = await renderWaitlisted()

    await advance(POLL_MS - 1)

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('skips the poll while the tab is hidden', async () => {
    const { get } = await renderWaitlisted()
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')

    await advance(POLL_MS * 2)

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('stops polling when the page unmounts', async () => {
    const { get, view } = await renderWaitlisted()

    expect(vi.getTimerCount()).toBe(1)
    view.unmount()
    expect(vi.getTimerCount()).toBe(0)
    await advance(POLL_MS * 3)

    expect(get).toHaveBeenCalledTimes(1)
  })
})
