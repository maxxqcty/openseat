import { Link, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useAuthContext } from './AuthProvider'

export interface HeaderUser {
  displayName: string
}

interface HeaderProps {
  user?: HeaderUser | null
}

interface PrimaryLink {
  label: string
  to: string
  isActive: (pathname: string) => boolean
}

const primaryLinks: PrimaryLink[] = [
  {
    label: 'Browse',
    to: '/',
    isActive: (pathname) => pathname === '/' || /^\/sessions\/[^/]+$/.test(pathname),
  },
  {
    label: 'My bookings',
    to: '/me',
    isActive: (pathname) => pathname === '/me',
  },
  {
    label: 'Host',
    to: '/host',
    isActive: (pathname) =>
      pathname === '/host' ||
      pathname === '/host/sessions/new' ||
      /^\/host\/sessions\/[^/]+$/.test(pathname),
  },
]

const linkBase =
  'block rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-focus-ring'

function linkClass(active: boolean): string {
  return `${linkBase} ${
    active ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-muted/10 hover:text-text'
  }`
}

interface LinkListProps {
  pathname: string
  onNavigate?: () => void
}

function LinkList({ pathname, onNavigate }: LinkListProps) {
  return (
    <ul className="flex flex-col gap-1 md:flex-row md:items-center md:gap-1">
      {primaryLinks.map((link) => {
        const active = link.isActive(pathname)
        return (
          <li key={link.to}>
            <Link
              to={link.to}
              aria-current={active ? 'page' : undefined}
              className={linkClass(active)}
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
  onNavigate?: () => void
}

function AuthActions({ user, onNavigate }: AuthActionsProps) {
  const { logout } = useAuthContext()
  const handleLogout = async () => {
    await logout()
    onNavigate?.()
  }

  if (user) {
    return (
      <div className="flex flex-col gap-1 md:flex-row md:items-center">
        <span className="px-3 py-2 text-sm font-medium text-text">{user.displayName}</span>
        <button
          type="button"
          className="rounded-md px-3 py-2 text-left text-sm font-medium text-muted transition-colors hover:bg-muted/10 hover:text-text md:text-center"
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
        to="/login"
        onClick={onNavigate}
        className="rounded-md px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-muted/10 hover:text-text"
      >
        Sign in
      </Link>
      <Link
        to="/signup"
        onClick={onNavigate}
        className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-surface transition-colors hover:bg-primary/90"
      >
        Create account
      </Link>
    </div>
  )
}

export function Header({ user = null }: HeaderProps) {
  const { pathname } = useLocation()
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
    <header className="border-b border-muted/20 bg-surface">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
        <Link
          to="/"
          className="rounded-md text-lg font-bold text-primary"
          onClick={() => setMenuOpen(false)}
        >
          OpenSeat
        </Link>

        <button
          ref={menuButtonRef}
          type="button"
          className="rounded-md border border-muted/30 px-3 py-2 text-sm font-medium text-text md:hidden"
          aria-expanded={menuOpen}
          aria-controls="primary-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          Menu
        </button>

        <nav aria-label="Primary" className="order-last w-full md:order-none md:w-auto">
          <div className="hidden md:flex md:items-center md:gap-2">
            <LinkList pathname={pathname} />
            <div className="ml-2 flex items-center gap-1 border-l border-muted/20 pl-2">
              <AuthActions user={user} />
            </div>
          </div>

          <div id="primary-menu" hidden={!menuOpen} className="md:hidden">
            {menuOpen && (
              <div className="space-y-2 border-t border-muted/20 py-3">
                <LinkList pathname={pathname} onNavigate={() => setMenuOpen(false)} />
                <div className="border-t border-muted/20 pt-2">
                  <AuthActions user={user} onNavigate={() => setMenuOpen(false)} />
                </div>
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}
