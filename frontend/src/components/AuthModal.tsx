import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { authHref, safeReturnTo, type AuthMode } from '../lib/auth-links'
import { useAuthContext } from './AuthProvider'
import { Button } from './Button'
import { Input } from './Input'
import { SeatIcon } from './icons'

const copy: Record<AuthMode, { title: string; blurb: string; submit: string; busy: string }> = {
  login: {
    title: 'Sign in',
    blurb: 'Welcome back. Pick up where you left off.',
    submit: 'Sign in',
    busy: 'Signing in…',
  },
  signup: {
    title: 'Create account',
    blurb: 'Book seats, join waitlists, or host your own workshop.',
    submit: 'Create account',
    busy: 'Creating account…',
  },
}

interface DialogProps {
  mode: AuthMode
  returnTo: string | null
}

function AuthDialog({ mode, returnTo }: DialogProps) {
  const { login, register } = useAuthContext()
  const navigate = useNavigate()
  const location = useLocation()
  const dialogRef = useRef<HTMLDivElement>(null)
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const text = copy[mode]
  const otherMode: AuthMode = mode === 'login' ? 'signup' : 'login'

  function close() {
    navigate({ pathname: location.pathname, search: '' }, { replace: true })
  }

  // Escape closes; the page behind stays put and cannot scroll while open.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        navigate({ pathname: location.pathname, search: '' }, { replace: true })
      }
    }
    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      previouslyFocused?.focus?.()
    }
  }, [navigate, location.pathname])

  // Keep Tab inside the dialog.
  function trapFocus(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'Tab' || !dialogRef.current) return
    const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled])',
    )
    if (focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(displayName, email, password)
      }
      navigate(safeReturnTo(returnTo), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-primary-dark/60 backdrop-blur-sm"
        onClick={close}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        onKeyDown={trapFocus}
        className="animate-float-in relative w-full max-w-md rounded-3xl bg-card p-7 shadow-2xl sm:p-8"
      >
        <button
          type="button"
          aria-label="Close"
          onClick={close}
          className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-muted/10 hover:text-text"
        >
          <span aria-hidden="true" className="text-xl leading-none">
            ×
          </span>
        </button>

        <span
          aria-hidden="true"
          className="grid h-11 w-11 place-items-center rounded-xl bg-primary text-surface shadow-sm"
        >
          <SeatIcon className="h-6 w-6" />
        </span>
        <h2 id="auth-title" className="mt-4 text-3xl font-bold tracking-tight text-text">
          {text.title}
        </h2>
        <p className="mt-1 text-sm text-muted">{text.blurb}</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {error && (
            <p role="alert" className="rounded-lg bg-danger/10 px-3 py-2 text-sm font-medium text-danger">
              {error}
            </p>
          )}
          {mode === 'signup' && (
            <Input
              label="Display name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
              autoComplete="name"
              autoFocus
            />
          )}
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            autoFocus={mode === 'login'}
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            minLength={mode === 'signup' ? 8 : undefined}
          />
          <Button type="submit" disabled={submitting} className="w-full py-3">
            {submitting ? text.busy : text.submit}
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-muted">
          {mode === 'login' ? 'New here? ' : 'Already have an account? '}
          <Link
            to={authHref(otherMode, returnTo ?? undefined)}
            replace
            className="font-semibold text-primary hover:text-primary-dark"
          >
            {mode === 'login' ? 'Create an account' : 'Sign in'}
          </Link>
        </p>
      </div>
    </div>
  )
}

/** The sign-in and sign-up dialog. It is open whenever the URL carries `?auth=login|signup`. */
export function AuthModal() {
  const { user } = useAuthContext()
  const [params] = useSearchParams()
  const mode = params.get('auth')

  if (user || (mode !== 'login' && mode !== 'signup')) return null
  return <AuthDialog key={mode} mode={mode} returnTo={params.get('returnTo')} />
}
