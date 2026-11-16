import { Link } from 'react-router-dom'
import {
  CtaBand,
  Faq,
  FeatureBento,
  PromotionStory,
  RotatingWord,
  StatsBand,
} from '../components/LandingSections'
import { Reveal } from '../components/Reveal'
import { authHref } from '../lib/auth-links'
import { SeatMap } from '../components/SeatMap'

const highlights = ['Never overbooked', 'Automatic waitlist', 'Check-in at the door']

/** Decorative seats drifting in the hero background. */
const floaters = [
  { className: 'left-[47%] top-[14%] h-8 w-8 animate-drift', tone: 'bg-white/10' },
  { className: 'left-[52%] bottom-[10%] h-6 w-6 animate-bob', tone: 'bg-emerald-300/30' },
  { className: 'right-[3%] top-[10%] h-10 w-10 animate-drift', tone: 'bg-emerald-300/15' },
  { className: 'right-[2%] bottom-[22%] h-7 w-7 animate-bob', tone: 'bg-white/10' },
]

/**
 * The signed-out front door: what OpenSeat is and two ways in. It deliberately
 * has no session list and no booking controls; those live on /sessions.
 */
export function LandingPage() {
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-950 via-primary-dark to-primary text-surface">
        <div aria-hidden="true" className="bg-dotgrid pointer-events-none absolute inset-0 opacity-20" />
        <div
          aria-hidden="true"
          className="animate-drift pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-emerald-400/20 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="animate-drift pointer-events-none absolute -bottom-32 left-1/4 h-80 w-80 rounded-full bg-emerald-300/10 blur-3xl [animation-delay:-6s]"
        />
        {floaters.map((floater, index) => (
          <span
            key={index}
            aria-hidden="true"
            className={`pointer-events-none absolute rounded-lg ${floater.tone} ${floater.className}`}
          />
        ))}

        <div className="relative mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 pt-32 sm:pb-28 sm:pt-40 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="animate-float-in">
            <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100">
              <span className="animate-seat-pulse h-1.5 w-1.5 rounded-full bg-emerald-300" />
              Workshop bookings
            </p>
            <h1 className="text-shimmer mt-6 text-5xl font-bold tracking-tight sm:text-7xl">OpenSeat</h1>
            <RotatingWord />
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-emerald-50/90 sm:text-xl">
              Fill every seat, without overbooking. One roster, one waitlist, and automatic
              promotion when someone cancels.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link
                to={authHref('signup')}
                className="rounded-full bg-card px-7 py-3 text-sm font-semibold text-primary-dark shadow-lg transition-all hover:-translate-y-0.5 hover:shadow-xl"
              >
                Get started
              </Link>
              <Link
                to={authHref('login')}
                className="rounded-full border border-white/40 px-7 py-3 text-sm font-semibold transition-colors hover:bg-white/10"
              >
                Sign in
              </Link>
            </div>
            <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm text-emerald-100/90" role="list">
              {highlights.map((item, index) => (
                <li
                  key={item}
                  style={{ animationDelay: `${400 + index * 150}ms` }}
                  className="animate-float-in flex items-center gap-2"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="hidden lg:block">
            <SeatMap />
          </div>
        </div>
      </section>

      <StatsBand />

      <section className="mx-auto max-w-6xl px-4 py-16">
        <Reveal>
          <p className="text-center text-xs font-bold uppercase tracking-[0.25em] text-primary">
            How a seat gets filled
          </p>
          <h2 className="mt-3 text-center text-3xl font-bold tracking-tight text-text sm:text-4xl">
            From sign-up sheet to full room
          </h2>
        </Reveal>
        <PromotionStory />
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16">
        <Reveal>
          <p className="text-center text-xs font-bold uppercase tracking-[0.25em] text-primary">
            Built for small rooms
          </p>
          <h2 className="mt-3 text-center text-3xl font-bold tracking-tight text-text sm:text-4xl">
            Everything a host needs, nothing they don&apos;t
          </h2>
        </Reveal>
        <FeatureBento />
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-20">
        <Reveal>
          <p className="text-center text-xs font-bold uppercase tracking-[0.25em] text-primary">
            Questions
          </p>
          <h2 className="mt-3 text-center text-3xl font-bold tracking-tight text-text sm:text-4xl">
            Good to know
          </h2>
        </Reveal>
        <Reveal delay={100}>
          <Faq />
        </Reveal>
      </section>

      <CtaBand />
    </>
  )
}
