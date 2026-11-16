import { Link, Outlet } from 'react-router-dom'
import { AuthModal } from './AuthModal'
import { Header, type HeaderUser } from './Header'

interface AppLayoutProps {
  user?: HeaderUser | null
}

export function AppLayout({ user = null }: AppLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-cream text-text">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-4 focus:py-2 focus:font-semibold focus:text-primary"
      >
        Skip to main content
      </a>
      <Header user={user} />
      <AuthModal />
      <main id="main-content" tabIndex={-1} className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-muted/15 bg-primary-dark text-emerald-50">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-display text-2xl font-bold">OpenSeat</p>
            <p className="mt-1 text-sm text-emerald-100/80">Fill every seat, without overbooking.</p>
          </div>
          {user && (
            <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2 text-sm font-medium">
              <Link to="/sessions" className="hover:text-white">Events</Link>
              <Link to="/me" className="hover:text-white">My bookings</Link>
              <Link to="/host" className="hover:text-white">Host a session</Link>
            </nav>
          )}
        </div>
      </footer>
    </div>
  )
}
