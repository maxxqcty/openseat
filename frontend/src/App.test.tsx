import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from './App'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App', () => {
  it('renders the OpenSeat landing page with a sign-in link', () => {
    renderAt('/')

    expect(screen.getByRole('heading', { level: 1, name: 'OpenSeat' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login')
  })

  it('renders the sign-in placeholder on the login route', () => {
    renderAt('/login')

    expect(screen.getByRole('heading', { level: 1, name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to OpenSeat' })).toHaveAttribute('href', '/')
  })
})
