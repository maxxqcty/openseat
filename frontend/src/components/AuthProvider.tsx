import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../services'
import type { User } from '../services/types'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (displayName: string, email: string, password: string) => Promise<User>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    api.auth.me().then((u) => {
      if (mounted) {
        setUser(u)
        setLoading(false)
      }
    }).catch(() => {
      if (mounted) {
        setUser(null)
        setLoading(false)
      }
    })
    return () => { mounted = false }
  }, [])

  async function login(email: string, password: string): Promise<User> {
    const u = await api.auth.login(email, password)
    setUser(u)
    return u
  }

  async function register(displayName: string, email: string, password: string): Promise<User> {
    const u = await api.auth.register(displayName, email, password)
    setUser(u)
    return u
  }

  async function logout() {
    await api.auth.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}