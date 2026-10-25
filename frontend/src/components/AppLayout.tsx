import { Outlet } from 'react-router-dom'
import { Header, type HeaderUser } from './Header'

interface AppLayoutProps {
  user?: HeaderUser | null
}

export function AppLayout({ user = null }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-surface text-text">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:font-semibold focus:text-primary"
      >
        Skip to main content
      </a>
      <Header user={user} />
      <main id="main-content" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  )
}
