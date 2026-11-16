import { describe, expect, it } from 'vitest'
import { hasSessionEnded, isCheckInWindowOpen } from './date'

const START = '2030-01-01T12:00:00.000Z'
const start = Date.parse(START)
const HOUR = 60 * 60 * 1000

describe('isCheckInWindowOpen', () => {
  it('opens exactly two hours before the start', () => {
    expect(isCheckInWindowOpen(START, 60, start - 2 * HOUR - 1)).toBe(false)
    expect(isCheckInWindowOpen(START, 60, start - 2 * HOUR)).toBe(true)
  })

  it('stays open until the session ends, then closes', () => {
    expect(isCheckInWindowOpen(START, 60, start + HOUR)).toBe(true)
    expect(isCheckInWindowOpen(START, 60, start + HOUR + 1)).toBe(false)
  })
})

describe('hasSessionEnded', () => {
  it('is false while the session is running and true after it ends', () => {
    expect(hasSessionEnded(START, 60, start + 30 * 60 * 1000)).toBe(false)
    expect(hasSessionEnded(START, 60, start + HOUR + 1)).toBe(true)
  })
})
