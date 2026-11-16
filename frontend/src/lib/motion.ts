import { useEffect, useRef, useState, type RefObject } from 'react'

/**
 * Motion is on only when the browser can observe elements and the person has
 * not asked for reduced motion. Test environments (no matchMedia) and visitors
 * who prefer less motion get the final, static state straight away.
 */
export function motionAllowed(): boolean {
  if (typeof window === 'undefined') return false
  if (typeof window.matchMedia !== 'function') return false
  if (typeof IntersectionObserver === 'undefined') return false
  return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** True once the element has scrolled into view (and stays true). */
export function useInView<T extends Element>(threshold = 0.2): [RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null)
  // When motion is off the element counts as already visible.
  const [seen, setSeen] = useState(() => !motionAllowed())

  useEffect(() => {
    const node = ref.current
    if (seen || !node) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setSeen(true)
          observer.disconnect()
        }
      },
      { threshold },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [seen, threshold])

  return [ref, seen]
}

/** Advances 0..count-1 on a timer. Stays at `rest` when motion is off. */
export function useCycle(count: number, intervalMs: number, rest = 0): number {
  const [index, setIndex] = useState(rest)

  useEffect(() => {
    if (!motionAllowed()) return
    const timer = window.setInterval(() => setIndex((value) => (value + 1) % count), intervalMs)
    return () => window.clearInterval(timer)
  }, [count, intervalMs])

  return index
}
