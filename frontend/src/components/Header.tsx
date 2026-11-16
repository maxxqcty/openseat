import { Link, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useAuthContext } from './AuthProvider'
import { authHref } from '../lib/auth-links'
import { SeatIcon } from './icons'

export interface HeaderUser {
  displayName: string
}

interface HeaderProps {
  user?: HeaderUser | null
}

interface PrimaryLink {
  label: string
  to: string
  /** Shown only to signed-in users. */
  requiresAuth?: boolean
  isActive: (pathname: string) => boolean
}

const primaryLinks: PrimaryLink[] = [
  {
    label: 'Events',
    to: '/sessions',
    requiresAuth: true,
    isActive: (pathname) => pathname === '/sessions' || /^\/sessions\/[^/]*$/.test(pathname),
  },
  {
    label: 'My bookings',
    to: '/me',
    requiresAuth: true,
    isActive: (pathname) => pathname === '/me',
  },
  {
    label: 'Host',
    to: '/host',
    requiresAuth: true,
    isActive: (pathname) =>
      pathname === '/host' ||
      pathname === '/host/sessions/new' ||
      /^\/host\/sessions\/[^/]+$/.test(pathname),
  },
]

/**
 * On the landing page the header floats over the green hero in white, so the
 * page reads as one surface. Everywhere else it sits on the cream page.
 */
function isOnHero(pathname: string): boolean {
  return pathname === '/'
}

const linkBase =
  'block rounded-full px-3.5 py-2 text-sm font-medium transition-colors focus-visible:outline-focus-ring'

function linkClass(active: boolean, onHero: boolean): string {
  if (onHero) {
    return `${linkBase} ${
      active ? 'bg-white/20 text-white' : 'text-emerald-50/85 hover:bg-white/10 hover:text-white'
    }`
  }
  return `${linkBase} ${
    active ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-primary/5 hover:text-text'
  }`
}

interface LinkListProps {
  pathname: string
  signedIn: boolean
  onHero: boolean
  onNavigate?: () => void
}

function LinkList({ pathname, signedIn, onHero, onNavigate }: LinkListProps) {
  return (
    <ul className="flex flex-col gap-1 md:flex-row md:items-center md:gap-1">
      {primaryLinks
        .filter((link) => signedIn || !link.requiresAuth)
        .map((link) => {
          const active = link.isActive(pathname)
          return (
            <li key={link.to}>
              <Link
                to={link.to}
                aria-current={active ? 'page' : undefined}
                className={linkClass(active, onHero)}
                onClick={onNavigate}
              >
                {link.label}
              </Link>
            </li>
          )
        })}
    </ul>
  )
}

interface AuthActionsProps {
  user?: HeaderUser | null
  onHero: boolean
  onNavigate?: () => void
}

function AuthActions({ user, onHero, onNavigate }: AuthActionsProps) {
  const { logout } = useAuthContext()
  const handleLogout = async () => {
    await logout()
    onNavigate?.()
  }

  const quiet = onHero
    ? 'text-emerald-50/85 hover:bg-white/10 hover:text-white'
    : 'text-muted hover:bg-primary/5 hover:text-text'

  if (user) {
    return (
      <div className="flex flex-col gap-1 md:flex-row md:items-center">
        <span
          className={`flex items-center gap-2 px-3 py-2 text-sm font-medium ${onHero ? 'text-white' : 'text-text'}`}
        >
          <span
            aria-hidden="true"
            className={`grid h-6 w-6 place-items-center rounded-full text-xs font-bold ${
              onHero ? 'bg-white/20 text-white' : 'bg-primary/15 text-primary'
            }`}
          >
            {user.displayName.charAt(0).toUpperCase()}
          </span>
          {user.displayName}
        </span>
        <button
          type="button"
          className={`rounded-full px-3.5 py-2 text-left text-sm font-medium transition-colors md:text-center ${quiet}`}
          onClick={handleLogout}
        >
          Sign out
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1 md:flex-row md:items-center">
      <Link
        to={authHref('login')}
        onClick={onNavigate}
        className={`rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${quiet}`}
      >
        Sign in
      </Link>
      <Link
        to={authHref('signup')}
        onClick={onNavigate}
        className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
          onHero
            ? 'bg-emerald-200 text-primary-dark hover:bg-emerald-100'
            : 'bg-primary text-surface shadow-sm hover:bg-primary-dark'
        }`}
      >
        Create account
      </Link>
    </div>
  )
}

export function Header({ user = null }: HeaderProps) {
  const { pathname } = useLocation()
  const onHero = isOnHero(pathname)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!menuOpen) {
      return
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        menuButtonRef.current?.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [menuOpen])

  return (
    <header
      className={
        onHero
          ? 'absolute inset-x-0 top-0 z-40 text-white'
          : 'sticky top-0 z-40 border-b border-muted/10 bg-cream/80 backdrop-blur'
      }
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3.5">
        <Link
          to={user ? '/sessions' : '/'}
          className={`flex items-center gap-2 rounded-md font-display text-xl font-bold ${
            onHero ? 'text-white' : 'text-primary-dark'
          }`}
          onClick={() => setMenuOpen(false)}
        >
          <span
            aria-hidden="true"
            className={`grid h-8 w-8 place-items-center rounded-lg shadow-sm ${
              onHero ? 'bg-white/15 text-white ring-1 ring-white/25' : 'bg-primary text-surface'
            }`}
          >
            <SeatIcon className="h-[18px] w-[18px]" />
          </span>
          OpenSeat
        </Link>

        <button
          ref={menuButtonRef}
          type="button"
          className={`rounded-full border px-3.5 py-2 text-sm font-medium md:hidden ${
            onHero ? 'border-white/30 text-white' : 'border-muted/25 bg-card text-text'
          }`}
          aria-expanded={menuOpen}
          aria-controls="primary-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          Menu
        </button>

        <nav aria-label="Primary" className="order-last w-full md:order-none md:w-auto">
          <div className="hidden md:flex md:items-center md:gap-3">
            {user && (
              <div
                className={`rounded-full border p-1 ${
                  onHero
                    ? 'border-white/15 bg-white/10 backdrop-blur'
                    : 'border-muted/15 bg-card shadow-sm'
                }`}
              >
                <LinkList pathname={pathname} signedIn onHero={onHero} />
              </div>
            )}
            <AuthActions user={user} onHero={onHero} />
          </div>

          <div id="primary-menu" hidden={!menuOpen} className="md:hidden">
            {menuOpen && (
              <div
                className={`mt-2 space-y-2 rounded-2xl p-3 ${
                  onHero
                    ? 'bg-primary-dark/95 backdrop-blur'
                    : 'border border-muted/15 bg-card shadow-md'
                }`}
              >
                {user && (
                  <LinkList
                    pathname={pathname}
                    signedIn
                    onHero={onHero}
                    onNavigate={() => setMenuOpen(false)}
                  />
                )}
                <div
                  className={`${user ? 'border-t pt-2' : ''} ${onHero ? 'border-white/15' : 'border-muted/15'}`}
                >
                  <AuthActions user={user} onHero={onHero} onNavigate={() => setMenuOpen(false)} />
                </div>
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}
