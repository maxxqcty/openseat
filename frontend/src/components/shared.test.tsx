import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Button, EmptyState, ErrorState, Input, StatusBadge } from './index'

describe('Button', () => {
  it('defaults to type button and forwards clicks', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })

    expect(button).toHaveAttribute('type', 'button')
    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('does not fire onClick while disabled', () => {
    const onClick = vi.fn()
    render(
      <Button onClick={onClick} disabled>
        Save
      </Button>,
    )

    const button = screen.getByRole('button', { name: 'Save' })

    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('supports an explicit submit type for forms', () => {
    render(<Button type="submit">Create</Button>)

    expect(screen.getByRole('button', { name: 'Create' })).toHaveAttribute('type', 'submit')
  })
})

describe('Input', () => {
  it('associates its label and input', () => {
    render(<Input label="Email" name="email" />)

    expect(screen.getByLabelText('Email')).toHaveAttribute('name', 'email')
  })

  it('links an error message with aria attributes', () => {
    render(<Input label="Email" error="Enter a valid email" />)

    const input = screen.getByLabelText('Email')
    const error = screen.getByText('Enter a valid email')

    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', error.id)
  })
})

describe('StatusBadge', () => {
  it.each([
    ['confirmed', 'Confirmed'],
    ['waitlisted', 'Waitlisted'],
    ['checked_in', 'Checked in'],
    ['cancelled', 'Cancelled'],
  ] as const)('renders visible text for %s', (status, label) => {
    render(<StatusBadge status={status} />)

    expect(screen.getByText(label)).toBeInTheDocument()
  })
})

describe('EmptyState and ErrorState', () => {
  it('renders a heading, message, and optional action', () => {
    render(
      <EmptyState
        title="No sessions yet"
        message="Check back soon."
        action={<Button>Browse</Button>}
      />,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'No sessions yet' })).toBeInTheDocument()
    expect(screen.getByText('Check back soon.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Browse' })).toBeInTheDocument()
  })

  it('announces errors and supports an optional action', () => {
    render(
      <ErrorState
        title="Could not load sessions"
        message="Try again."
        action={<Button variant="secondary">Retry</Button>}
      />,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Could not load sessions' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Try again.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
