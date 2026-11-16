export type AuthMode = 'login' | 'signup'

/**
 * Sign-in and sign-up live in a dialog opened by `?auth=login|signup`, so every
 * "sign in" link in the app is just a link to the landing page with that flag.
 * `returnTo` is where to go once signed in.
 */
export function authHref(mode: AuthMode, returnTo?: string): string {
  const returnPart = returnTo ? `&returnTo=${encodeURIComponent(returnTo)}` : ''
  return `/?auth=${mode}${returnPart}`
}

/** Accept only same-site paths, and never loop back into the dialog itself. */
export function safeReturnTo(value: string | null, fallback = '/sessions'): string {
  if (!value) return fallback
  if (!value.startsWith('/') || value.startsWith('//')) return fallback
  if (value === '/' || value.startsWith('/?') || value.startsWith('/login') || value.startsWith('/signup')) {
    return fallback
  }
  return value
}
