import { expect, test, type Page } from '@playwright/test'

/**
 * The acceptance journey: a host, and two guests competing for one seat.
 *
 * Emails and the session title carry a run stamp so a shared environment can
 * be reused without collisions. Everything else is driven through the UI, with
 * the documented API errors checked through the same browser contexts so the
 * cookies are the real ones.
 */

const PASSWORD = 'e2e-password-123'
const RUN = Date.now()
const HOST_EMAIL = `host-${RUN}@example.com`
const GUEST_A_EMAIL = `guest-a-${RUN}@example.com`
const GUEST_B_EMAIL = `guest-b-${RUN}@example.com`
const SESSION_TITLE = `E2E Workshop ${RUN}`
const CSRF_HEADERS = { 'X-Requested-With': 'openseat' }

async function signUp(page: Page, displayName: string, email: string): Promise<void> {
  await page.goto('/signup')
  await page.getByLabel('Display name').fill(displayName)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}

/** A `datetime-local` value in the browser's zone, relative to now. */
function localDateTime(minutesFromNow: number): string {
  const date = new Date(Date.now() + minutesFromNow * 60_000)
  const pad = (value: number) => String(value).padStart(2, '0')
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return `${day}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

test('host, guest A, and guest B complete the booking, promotion, and check-in journey', async ({
  browser,
}) => {
  const hostContext = await browser.newContext()
  const guestAContext = await browser.newContext()
  const guestBContext = await browser.newContext()
  const host = await hostContext.newPage()
  const guestA = await guestAContext.newPage()
  const guestB = await guestBContext.newPage()

  try {
    await signUp(host, 'E2E Host', HOST_EMAIL)

    // A session with one seat that starts inside the check-in window, so the
    // host can check a guest in during the same run.
    await host.goto('/host/sessions/new')
    await host.getByLabel('Title').fill(SESSION_TITLE)
    await host.getByLabel('Start date & time').fill(localDateTime(30))
    await host.getByLabel('Capacity').fill('1')
    await host.getByLabel('Location').fill('E2E Studio')
    await host.getByRole('button', { name: 'Create session' }).click()

    await expect(host).toHaveURL(/\/host\/sessions\/[0-9a-f-]{36}$/)
    const sessionId = new URL(host.url()).pathname.split('/').pop()
    expect(sessionId).toBeTruthy()
    const guestPath = `/sessions/${sessionId}`
    const hostPath = `/host/sessions/${sessionId}`

    // Guest A takes the only seat.
    await signUp(guestA, 'E2E Guest A', GUEST_A_EMAIL)
    await guestA.goto(guestPath)
    await guestA.getByRole('button', { name: 'Book seat' }).click()
    await expect(guestA.getByRole('alert')).toContainText('Booking confirmed')
    await expect(guestA.getByText('Status:')).toContainText('Confirmed')

    // Guest B lands on the waitlist at position 1.
    await signUp(guestB, 'E2E Guest B', GUEST_B_EMAIL)
    await guestB.goto(guestPath)
    await guestB.getByRole('button', { name: 'Join waitlist' }).click()
    await expect(guestB.getByRole('alert')).toContainText('Waitlisted, position 1')
    await expect(guestB.getByText('Status:')).toContainText('Waitlisted, position 1')

    // Documented failures, using A's real session cookie.
    const duplicate = await guestA.request.post(`/api/sessions/${sessionId}/bookings`, {
      headers: CSRF_HEADERS,
    })
    expect(duplicate.status()).toBe(409)
    expect((await duplicate.json()).error.code).toBe('booking_conflict')

    const noCsrf = await guestA.request.post(`/api/sessions/${sessionId}/bookings`)
    expect(noCsrf.status()).toBe(403)
    expect((await noCsrf.json()).error.code).toBe('forbidden')

    // A is signed in but is not the host, so check-in must be forbidden.
    const guestBBookings = await guestB.request.get('/api/me/bookings')
    const [guestBBooking] = (await guestBBookings.json()) as Array<{ id: string }>
    const nonHostCheckIn = await guestA.request.post(
      `/api/bookings/${guestBBooking.id}/check-in`,
      { headers: CSRF_HEADERS },
    )
    expect(nonHostCheckIn.status()).toBe(403)

    // A cancels and B is promoted by the server. A cancelled booking is no
    // longer active, so A's page drops "Your booking" and offers the waitlist.
    await guestA.getByRole('button', { name: 'Cancel booking' }).click()
    await expect(guestA.getByRole('alert')).toContainText('Booking cancelled')
    await expect(guestA.getByRole('button', { name: 'Join waitlist' })).toBeVisible()

    // B's page polls every 10s; a bounded assertion is the poll.
    await expect(guestB.getByText('Status:')).toContainText('Confirmed', { timeout: 30_000 })

    // The host checks B in and the roster moves with it.
    await host.goto(hostPath)
    const confirmedSection = host
      .locator('section')
      .filter({ has: host.getByRole('heading', { name: 'Confirmed (1)' }) })
    await expect(confirmedSection.getByText('E2E Guest B')).toBeVisible()
    await confirmedSection.getByRole('button', { name: 'Check in' }).click()

    const checkedInSection = host
      .locator('section')
      .filter({ has: host.getByRole('heading', { name: 'Checked in (1)' }) })
    const checkedInEntry = checkedInSection.locator('li').filter({ hasText: 'E2E Guest B' })
    await expect(checkedInEntry).toBeVisible()
    await expect(checkedInEntry.getByText(/^Checked in/)).toBeVisible()

    // B sees the result on the next poll, without a manual reload.
    await expect(guestB.getByText('Status:')).toContainText('Checked in', { timeout: 30_000 })
  } finally {
    await hostContext.close()
    await guestAContext.close()
    await guestBContext.close()
  }
})

test('anonymous requests are rejected before any resource lookup', async ({ request }) => {
  const missing = '00000000-0000-4000-8000-000000000000'

  const roster = await request.get(`/api/sessions/${missing}/bookings`)
  expect(roster.status()).toBe(401)

  const checkIn = await request.post(`/api/bookings/${missing}/check-in`, {
    headers: CSRF_HEADERS,
  })
  expect(checkIn.status()).toBe(401)
})
