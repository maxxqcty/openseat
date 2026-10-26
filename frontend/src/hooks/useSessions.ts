import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services'
import type { Session, SessionDetail } from '../services/types'

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  async function load() {
    if (!mountedRef.current) return
    try {
      setError(null)
      const data = await api.sessions.list()
      if (mountedRef.current) {
        setSessions(data)
        setLoading(false)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions')
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    mountedRef.current = true
    Promise.resolve().then(load)
    return () => { mountedRef.current = false }
  }, [])

  return { sessions, loading, error, reload: load }
}

export function useSessionDetail(sessionId: string) {
  const [session, setSession] = useState<SessionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const focusedRef = useRef(true)
  const mountedRef = useRef(true)

  const load = useCallback(async () => {
    if (!mountedRef.current) return
    try {
      setError(null)
      const data = await api.sessions.get(sessionId)
      if (mountedRef.current) {
        setSession(data)
        setLoading(false)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load session')
        setLoading(false)
      }
    }
  }, [sessionId])

  useEffect(() => {
    mountedRef.current = true
    Promise.resolve().then(load)
    intervalRef.current = window.setInterval(() => {
      if (focusedRef.current && document.visibilityState === 'visible') {
        load()
      }
    }, 10_000)

    function onFocus() { focusedRef.current = true }
    function onBlur() { focusedRef.current = false }
    function onVisibilityChange() {
      if (document.visibilityState === 'visible') {
        load()
      }
    }

    window.addEventListener('focus', onFocus)
    window.addEventListener('blur', onBlur)
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      mountedRef.current = false
      if (intervalRef.current) window.clearInterval(intervalRef.current)
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('blur', onBlur)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [sessionId, load])

  return { session, loading, error, reload: load }
}

export function useCreateSession() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  async function create(input: {
    title: string
    description?: string
    startsAt: string
    durationMinutes: number
    capacity: number
    location: string
  }) {
    if (!mountedRef.current) throw new Error('Component unmounted')
    try {
      setLoading(true)
      setError(null)
      const session = await api.sessions.create(input)
      if (mountedRef.current) {
        setLoading(false)
      }
      return session
    } catch (err) {
      if (mountedRef.current) {
        const msg = err instanceof Error ? err.message : 'Failed to create session'
        setError(msg)
        setLoading(false)
      }
      throw err
    }
  }

  return { create, loading, error }
}

export function useCancelSession() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  async function cancel(sessionId: string) {
    if (!mountedRef.current) throw new Error('Component unmounted')
    try {
      setLoading(true)
      setError(null)
      await api.sessions.cancel(sessionId)
      if (mountedRef.current) {
        setLoading(false)
      }
    } catch (err) {
      if (mountedRef.current) {
        const msg = err instanceof Error ? err.message : 'Failed to cancel session'
        setError(msg)
        setLoading(false)
      }
      throw err
    }
  }

  return { cancel, loading, error }
}

export function useHostSessions() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  async function load() {
    if (!mountedRef.current) return
    try {
      setError(null)
      const all = await api.sessions.list()
      if (mountedRef.current) {
        setSessions(all)
        setLoading(false)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions')
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    mountedRef.current = true
    Promise.resolve().then(load)
    return () => { mountedRef.current = false }
  }, [])

  return { sessions, loading, error, reload: load }
}