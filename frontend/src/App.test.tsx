import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from './App'

const routes = [
  ['/', 'OpenSeat'],
  ['/login', 'Sign in'],
  ['/signup', 'Create account'],
  ['/sessions/example', 'Session details'],
  ['/me', 'My bookings'],
  ['/host', 'Host dashboard'],
  ['/host/sessions/new', 'Create a session'],
  ['/host/sessions/example', 'Session roster'],
] as const

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App routes', () => {
  it.each(routes)('renders %s with the %s heading', (path, heading) => {
    renderAt(path)

    const main = screen.getByRole('main')
    const headings = within(main).getAllByRole('heading', { level: 1 })

    expect(headings).toHaveLength(1)
    expect(headings[0]).toHaveTextContent(heading)
    expect(headings[0].textContent?.trim()).not.toBe('')
    expect(screen.getAllByRole('banner')).toHaveLength(1)
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it.each(['/does-not-exist', '/host/does-not-exist', '/sessions/', '/host/sessions/'])(
    'renders the 404 page for %s',
    (path) => {
      renderAt(path)

      expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Back to browse' })).toHaveAttribute('href', '/')
    },
  )

  it('makes the skip link the first focusable element and targets the main landmark', () => {
    const { container } = renderAt('/')

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
