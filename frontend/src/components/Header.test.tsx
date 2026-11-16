import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'
import { AuthProvider } from './AuthProvider'

const activeCases = [
  ['/', null],
  ['/sessions', 'Events'],
  ['/sessions/', 'Events'],
  ['/sessions/example', 'Events'],
  ['/me', 'My bookings'],
  ['/host', 'Host'],
  ['/host/sessions/new', 'Host'],
  ['/host/sessions/example', 'Host'],
  ['/login', null],
  ['/signup', null],
  ['/does-not-exist', null],
  ['/host/does-not-exist', null],
  ['/host/sessions/', null],
] as const

function renderHeader(path = '/', user: { displayName: string } | null = null) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Header user={user} />
      </AuthProvider>
    </MemoryRouter>,
  )
}

function currentLinks() {
  return screen.getAllByRole('link').filter((link) => link.getAttribute('aria-current') === 'page')
}

describe('Header', () => {
  it('shows no events or bookings links to visitors, and no Browse link at all', () => {
    renderHeader()

    const nav = screen.getByRole('navigation', { name: 'Primary' })

    expect(within(nav).queryByRole('link', { name: 'Browse' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Events' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'My bookings' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Host' })).not.toBeInTheDocument()
  })

  it('shows Events, My bookings and Host when signed in', () => {
    renderHeader('/sessions', { displayName: 'Ada Lovelace' })

    const nav = screen.getByRole('navigation', { name: 'Primary' })

    expect(within(nav).getByRole('link', { name: 'Events' })).toHaveAttribute('href', '/sessions')
    expect(within(nav).getByRole('link', { name: 'My bookings' })).toHaveAttribute('href', '/me')
    expect(within(nav).getByRole('link', { name: 'Host' })).toHaveAttribute('href', '/host')
  })

  it('sends the logo to the landing page when signed out and to Browse when signed in', () => {
    const signedOut = renderHeader('/', null)
    expect(screen.getByRole('link', { name: 'OpenSeat' })).toHaveAttribute('href', '/')
    signedOut.unmount()

    renderHeader('/sessions', { displayName: 'Ada Lovelace' })
    expect(screen.getByRole('link', { name: 'OpenSeat' })).toHaveAttribute('href', '/sessions')
  })

  it.each(activeCases)('sets exactly the right current link on %s', (path, active) => {
    renderHeader(path, { displayName: 'Ada Lovelace' })

    const current = currentLinks()

    if (active === null) {
      expect(current).toHaveLength(0)
      return
    }

    expect(current).toHaveLength(1)
    expect(current[0]).toHaveTextContent(active)
    expect(current[0]).toHaveClass('bg-primary/10')
  })

  it('shows signed-out actions and no signed-in controls', () => {
    renderHeader('/', null)

    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/?auth=login')
    expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute(
      'href',
      '/?auth=signup',
    )
    expect(screen.queryByRole('button', { name: 'Sign out' })).not.toBeInTheDocument()
  })

  it('shows the display name and native sign-out button when signed in', () => {
    renderHeader('/', { displayName: 'Ada Lovelace' })

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign out' })).toHaveAttribute('type', 'button')
    expect(screen.queryByRole('link', { name: 'Sign in' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Create account' })).not.toBeInTheDocument()
  })

  it('opens and closes the mobile menu and exposes its links only when open', () => {
    renderHeader('/sessions', { displayName: 'Ada Lovelace' })

    const trigger = screen.getByRole('button', { name: 'Menu' })
    const panel = document.getElementById('primary-menu')

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveAttribute('aria-controls', 'primary-menu')
    expect(panel).toHaveAttribute('hidden')

    fireEvent.click(trigger)

    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(panel).not.toHaveAttribute('hidden')
    expect(panel).not.toBeNull()
    expect(within(panel as HTMLElement).getByRole('link', { name: 'Events' })).toHaveAttribute(
      'href',
      '/sessions',
    )

    fireEvent.click(within(panel as HTMLElement).getByRole('link', { name: 'Events' }))

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(panel).toHaveAttribute('hidden')
  })

  it('offers only sign in and create account in the visitor mobile menu', () => {
    renderHeader('/', null)

    fireEvent.click(screen.getByRole('button', { name: 'Menu' }))

    const panel = document.getElementById('primary-menu') as HTMLElement
    expect(within(panel).getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Sign in',
      'Create account',
    ])
  })

  it('closes the mobile menu on Escape and returns focus to the trigger', () => {
    renderHeader()

    const trigger = screen.getByRole('button', { name: 'Menu' })
    fireEvent.click(trigger)
    trigger.focus()

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(document.getElementById('primary-menu')).toHaveAttribute('hidden')
    expect(trigger).toHaveFocus()
  })

  it('shows signed-in controls in the open mobile menu', () => {
    renderHeader('/', { displayName: 'Ada Lovelace' })

    fireEvent.click(screen.getByRole('button', { name: 'Menu' }))

    const panel = document.getElementById('primary-menu') as HTMLElement
    expect(within(panel).getByText('Ada Lovelace')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Sign out' })).toBeInTheDocument()
    expect(within(panel).queryByRole('link', { name: 'Sign in' })).not.toBeInTheDocument()
  })
})
