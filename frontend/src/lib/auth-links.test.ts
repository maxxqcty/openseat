import { describe, expect, it } from 'vitest'
import { authHref, safeReturnTo } from './auth-links'

describe('safeReturnTo', () => {
  it('accepts local paths, including query strings', () => {
    expect(safeReturnTo('/sessions/s1')).toBe('/sessions/s1')
    expect(safeReturnTo('/host/sessions/s1?tab=roster')).toBe('/host/sessions/s1?tab=roster')
  })

  it.each([
    'https://evil.example/phish',
    'http://evil.example',
    '//evil.example/phish',
    'javascript:alert(1)',
    'sessions/s1',
    '',
  ])('rejects %j and falls back to the events list', (value) => {
    expect(safeReturnTo(value)).toBe('/sessions')
  })

  it('falls back when there is no returnTo', () => {
    expect(safeReturnTo(null)).toBe('/sessions')
  })

  it.each(['/', '/?auth=login', '/login', '/signup?returnTo=/me'])(
    'never loops back into the sign-in dialog via %s',
    (value) => {
      expect(safeReturnTo(value)).toBe('/sessions')
    },
  )

  it('honours a custom fallback', () => {
    expect(safeReturnTo('//evil.example', '/me')).toBe('/me')
  })
})

describe('authHref', () => {
  it('encodes returnTo into the sign-in link', () => {
    expect(authHref('login', '/sessions/s1?x=1')).toBe(
      '/?auth=login&returnTo=%2Fsessions%2Fs1%3Fx%3D1',
    )
  })

  it('omits returnTo when none is given', () => {
    expect(authHref('signup')).toBe('/?auth=signup')
  })
})
