import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'
import { mockApi, resetMock } from './services/mock'

const publicRoutes = [
  ['/', 'OpenSeat'],
  ['/login', 'Sign in'],
  ['/signup', 'Create account'],
] as const

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App routes', () => {
  beforeEach(() => {
    resetMock()
  })

  it.each(publicRoutes)('renders public route %s with the %s heading', async (path, heading) => {
    renderAt(path)

    // Wait for the heading to appear (data loaded)
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
    })
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('renders session detail page with a valid session', async () => {
    resetMock()
    const sessions = await mockApi.sessions.list()
    const sessionId = sessions[0].id

    renderAt(`/sessions/${sessionId}`)

    // Wait for the heading to appear (data loaded)
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: sessions[0].title })).toBeInTheDocument()
    })
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it.each(['/does-not-exist', '/host/does-not-exist', '/sessions/', '/host/sessions/'])(
    'renders the 404 page for %s',
    async (path) => {
      renderAt(path)

      expect(await screen.findByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Back to browse' })).toHaveAttribute('href', '/')
    },
  )

  it('makes the skip link the first focusable element and targets the main landmark', async () => {
    const { container } = renderAt('/')

    // Wait for the app to load past the auth loading spinner
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Skip to main content' })).toBeInTheDocument()
    })

    const skipLink = screen.getByRole('link', { name: 'Skip to main content' })
    const main = screen.getByRole('main')
    const focusable = container.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )

    expect(skipLink).toHaveAttribute('href', '#main-content')
    expect(main).toHaveAttribute('id', 'main-content')
    expect(main).toHaveAttribute('tabindex', '-1')
    expect(focusable[0]).toBe(skipLink)
  })
})
