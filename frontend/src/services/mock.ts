import type { Session } from './types'

const fakeSessions: Record<string, Session> = {
  s1: {
    id: 's1',
    title: 'Test session',
    capacity: 3,
    attendeeCount: 0,
    waitlistCount: 0,
    createdBy: 'user1',
  },
}

// ---------- in-memory store ----------

const sessions = new Map<string, Session>()
;(sessions as any).assign = function (entries: any) {
  for (const [k, v] of Object.entries(entries)) this.set(k, v)
}

// ---------- Api ----------

export const Api = {
  async list(): Promise<Session[]> {
    return [...sessions.values()]
  },

  async get(id: string): Promise<Session | null> {
    return sessions.get(id) ?? null
  },

  async create(_title: string, _capacity: number): Promise<Session> {
    const id = `s${sessions.size + 1}`
    const session: Session = {
      id,
      title: 'Test session',
      capacity: 3,
      attendeeCount: 0,
      waitlistCount: 0,
      createdBy: 'user1',
    }
    sessions.set(id, session)
    return session
  },

  async cancel(id: string): Promise<Session> {
    const session = sessions.get(id)
    if (session) session.attendeeCount = Math.max(0, session.attendeeCount - 1)
    return session!
  },

  async book(): Promise<any> {
    return { id: 'b1', sessionId: 's1', userId: 'user1', status: 'confirmed', createdAt: new Date().toISOString() }
  },

  async cancelBooking(): Promise<any> {
    return { id: 'b1', sessionId: 's1', userId: 'user1', status: 'cancelled', createdAt: new Date().toISOString() }
  },

  async checkIn(): Promise<any> {
    return { id: 'b1', sessionId: 's1', userId: 'user1', status: 'checked_in', checkedInAt: new Date().toISOString() }
  },

  async getRoster(): Promise<any[]> {
    return []
  },

  resetMock(): void {
    sessions.clear()
    ;(sessions as any).assign(Object.fromEntries(Object.entries(fakeSessions)))
  },
} as const