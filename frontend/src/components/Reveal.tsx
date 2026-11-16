import { useEffect, useState, type ReactNode } from 'react'
import { motionAllowed, useInView } from '../lib/motion'

export interface RevealProps {
  children: ReactNode
  /** Delay in milliseconds, to stagger siblings. */
  delay?: number
  className?: string
}

/** Fades and slides its children up the first time they scroll into view. */
export function Reveal({ children, delay = 0, className = '' }: RevealProps) {
  const [ref, seen] = useInView<HTMLDivElement>(0.15)
  return (
    <div
      ref={ref}
      style={{ transitionDelay: seen ? `${delay}ms` : '0ms' }}
      className={`transition-all duration-700 ease-out ${
        seen ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
      } ${className}`.trim()}
    >
      {children}
    </div>
  )
}

export interface CountUpProps {
  to: number
  durationMs?: number
  suffix?: string
}

/** Counts from 0 up to `to` when scrolled into view. Shows `to` at once if motion is off. */
export function CountUp({ to, durationMs = 1400, suffix = '' }: CountUpProps) {
  const [ref, seen] = useInView<HTMLSpanElement>(0.5)
  const [value, setValue] = useState(() => (motionAllowed() ? 0 : to))

  useEffect(() => {
    if (!seen || !motionAllowed()) return
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(to * eased))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [seen, to, durationMs])

  return (
    <span ref={ref}>
      {value}
      {suffix}
    </span>
  )
}
