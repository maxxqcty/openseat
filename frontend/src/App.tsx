import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { AuthProvider } from './components/AuthProvider'
import { CreateSessionPage } from './pages/CreateSessionPage'
import { HostDashboardPage } from './pages/HostDashboardPage'
import { HostSessionPage } from './pages/HostSessionPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { MyBookingsPage } from './pages/MyBookingsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SessionDetailPage } from './pages/SessionDetailPage'
import { SignupPage } from './pages/SignupPage'
import { useAuthContext } from './components/AuthProvider'

function AppRoutes() {
  const { user, loading } = useAuthContext()

  if (loading) {
    return (
      <div className="min-h-screen bg-surface text-text flex items-center justify-center">
        <div className="inline-flex items-center gap-2 text-muted">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>Loading…</span>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route element={<AppLayout user={user} />}>
        <Route index element={<LandingPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />
        <Route path="sessions/:id" element={<SessionDetailPage />} />
        <Route path="me" element={<MyBookingsPage />} />
        <Route path="host" element={<HostDashboardPage />} />
        <Route path="host/sessions/new" element={<CreateSessionPage />} />
        <Route path="host/sessions/:id" element={<HostSessionPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App