import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'
import { mockApi, resetMock } from './services/mock'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

async function signIn(email = 'host@example.com', password = 'password123') {
  await mockApi.auth.login(email, password)
}

describe('landing page', () => {
  beforeEach(() => {
    resetMock()
  })

  it('renders the pitch with the OpenSeat heading', async () => {
    renderAt('/')

    expect(await screen.findByRole('heading', { level: 1, name: 'OpenSeat' })).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('shows no events and no Browse link to visitors', async () => {
    const sessions = await mockApi.sessions.list()
    renderAt('/')

    await screen.findByRole('heading', { level: 1, name: 'OpenSeat' })
    expect(screen.queryByRole('link', { name: /browse/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Book seat' })).not.toBeInTheDocument()
    expect(screen.queryByText(sessions[0].title)).not.toBeInTheDocument()
  })

  it('opens sign-up and sign-in from the landing page calls to action', async () => {
    renderAt('/')

    await screen.findByRole('heading', { level: 1, name: 'OpenSeat' })
    const main = within(screen.getByRole('main'))
    expect(main.getByRole('link', { name: 'Get started' })).toHaveAttribute('href', '/?auth=signup')
    expect(main.getAllByRole('link', { name: 'Sign in' })[0]).toHaveAttribute('href', '/?auth=login')
  })

  it('answers common questions with native disclosure widgets', async () => {
    renderAt('/')

    await screen.findByRole('heading', { level: 1, name: 'OpenSeat' })
    const question = screen.getByText('What happens when someone cancels?')
    expect(question.closest('details')).not.toBeNull()
    expect(screen.getByText('Who can see my email address?')).toBeInTheDocument()
  })

  it('makes the skip link the first focusable element and targets the main landmark', async () => {
    const { container } = renderAt('/')

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

describe('sign-in and sign-up dialog', () => {
  beforeEach(() => {
    resetMock()
  })

  it.each([
    ['/login', 'Sign in'],
    ['/signup', 'Create account'],
    ['/?auth=login', 'Sign in'],
    ['/?auth=signup', 'Create account'],
  ])('opens as a dialog over the landing page for %s', async (path, title) => {
    renderAt(path)

    const dialog = await screen.findByRole('dialog', { name: title })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByRole('heading', { level: 1, name: 'OpenSeat' })).toBeInTheDocument()
  })

  it('is closed on a plain visit and closes on Escape and on the close button', async () => {
    renderAt('/?auth=login')
    await screen.findByRole('dialog', { name: 'Sign in' })

    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())

    renderAt('/?auth=signup')
    const dialogs = await screen.findAllByRole('dialog', { name: 'Create account' })
    fireEvent.click(within(dialogs[0]).getByRole('button', { name: 'Close' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('switches between sign-in and sign-up inside the dialog', async () => {
    renderAt('/?auth=login')
    const dialog = await screen.findByRole('dialog', { name: 'Sign in' })

    fireEvent.click(within(dialog).getByRole('link', { name: 'Create an account' }))

    const signup = await screen.findByRole('dialog', { name: 'Create account' })
    expect(within(signup).getByLabelText('Display name')).toBeInTheDocument()
  })

  it('signs in and lands on the events list', async () => {
    renderAt('/?auth=login')
    const dialog = await screen.findByRole('dialog', { name: 'Sign in' })

    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'host@example.com' } })
    fireEvent.change(within(dialog).getByLabelText('Password'), { target: { value: 'password123' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Find a workshop' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows an error and stays open when the password is wrong', async () => {
    renderAt('/?auth=login')
    const dialog = await screen.findByRole('dialog', { name: 'Sign in' })

    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'host@example.com' } })
    fireEvent.change(within(dialog).getByLabelText('Password'), { target: { value: 'wrong-password' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Sign in' }))

    expect(await within(dialog).findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('creates an account and lands on the events list', async () => {
    renderAt('/?auth=signup')
    const dialog = await screen.findByRole('dialog', { name: 'Create account' })

    fireEvent.change(within(dialog).getByLabelText('Display name'), { target: { value: 'New Person' } })
    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'new@example.com' } })
    fireEvent.change(within(dialog).getByLabelText('Password'), { target: { value: 'a-long-password' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Find a workshop' })).toBeInTheDocument()
  })
})

describe('events are for signed-in users', () => {
  beforeEach(() => {
    resetMock()
  })

  it.each(['/sessions', '/me', '/host', '/host/sessions/new'])(
    'sends a visitor from %s to the sign-in dialog',
    async (path) => {
      renderAt(path)

      expect(await screen.findByRole('dialog', { name: 'Sign in' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 1, name: 'OpenSeat' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'Find a workshop' })).not.toBeInTheDocument()
    },
  )

  it('keeps a visitor away from a single event until they sign in', async () => {
    const sessions = await mockApi.sessions.list()
    renderAt(`/sessions/${sessions[0].id}`)

    expect(await screen.findByRole('dialog', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1, name: sessions[0].title })).not.toBeInTheDocument()
  })

  it('returns to the page the visitor asked for after signing in', async () => {
    renderAt('/me')
    const dialog = await screen.findByRole('dialog', { name: 'Sign in' })

    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'host@example.com' } })
    fireEvent.change(within(dialog).getByLabelText('Password'), { target: { value: 'password123' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'My bookings' })).toBeInTheDocument()
  })

  it('sends a signed-in user from / straight to the events list', async () => {
    await signIn()
    renderAt('/')

    expect(await screen.findByRole('heading', { level: 1, name: 'Find a workshop' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1, name: 'OpenSeat' })).not.toBeInTheDocument()
  })

  it('lists events for a signed-in user and filters them with the search box', async () => {
    await signIn()
    const sessions = await mockApi.sessions.list()
    renderAt('/sessions')

    expect(await screen.findByRole('link', { name: new RegExp(sessions[0].title) })).toBeInTheDocument()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search sessions' }), {
      target: { value: 'zzz-no-such-workshop' },
    })

    expect(await screen.findByRole('heading', { name: 'No matches' })).toBeInTheDocument()
  })

  it('renders the session detail page for a signed-in user', async () => {
    await signIn()
    const sessions = await mockApi.sessions.list()

    renderAt(`/sessions/${sessions[0].id}`)

    expect(
      await screen.findByRole('heading', { level: 1, name: sessions[0].title }),
    ).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it.each(['/does-not-exist', '/host/does-not-exist', '/host/sessions/'])(
    'renders the 404 page for %s',
    async (path) => {
      renderAt(path)

      expect(await screen.findByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Back to home' })).toHaveAttribute('href', '/')
    },
  )
})
