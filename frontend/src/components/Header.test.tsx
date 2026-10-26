import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

const activeCases = [
  ['/', 'Browse'],
  ['/sessions/example', 'Browse'],
  ['/me', 'My bookings'],
  ['/host', 'Host'],
  ['/host/sessions/new', 'Host'],
  ['/host/sessions/example', 'Host'],
  ['/login', null],
  ['/signup', null],
  ['/does-not-exist', null],
  ['/host/does-not-exist', null],
  ['/sessions/', null],
  ['/host/sessions/', null],
] as const

function renderHeader(path = '/', user: { displayName: string } | null = null) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Header user={user} />
    </MemoryRouter>,
  )
}

function currentLinks() {
  return screen.getAllByRole('link').filter((link) => link.getAttribute('aria-current') === 'page')
}

describe('Header', () => {
  it('renders the primary navigation with the expected hrefs', () => {
    renderHeader()

    const nav = screen.getByRole('navigation', { name: 'Primary' })

    expect(within(nav).getByRole('link', { name: 'Browse' })).toHaveAttribute('href', '/')
    expect(within(nav).getByRole('link', { name: 'My bookings' })).toHaveAttribute('href', '/me')
    expect(within(nav).getByRole('link', { name: 'Host' })).toHaveAttribute('href', '/host')
  })

  it.each(activeCases)('sets exactly the right current link on %s', (path, active) => {
    renderHeader(path)

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

    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute('href', '/signup')
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
    renderHeader()

    const trigger = screen.getByRole('button', { name: 'Menu' })
    const panel = document.getElementById('primary-menu')

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveAttribute('aria-controls', 'primary-menu')
    expect(panel).toHaveAttribute('hidden')

    fireEvent.click(trigger)

    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(panel).not.toHaveAttribute('hidden')
    expect(panel).not.toBeNull()
    expect(within(panel as HTMLElement).getByRole('link', { name: 'Browse' })).toHaveAttribute(
      'href',
      '/',
    )

    fireEvent.click(within(panel as HTMLElement).getByRole('link', { name: 'Browse' }))

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(panel).toHaveAttribute('hidden')
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
