import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './components'
import { CreateSessionPage } from './pages/CreateSessionPage'
import { HostDashboardPage } from './pages/HostDashboardPage'
import { HostSessionPage } from './pages/HostSessionPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { MyBookingsPage } from './pages/MyBookingsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SessionDetailPage } from './pages/SessionDetailPage'
import { SignupPage } from './pages/SignupPage'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout user={null} />}>
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

export default App
