import { Link } from 'react-router-dom'
import { authHref } from '../lib/auth-links'
import { useCycle, useInView } from '../lib/motion'
import { CountUp, Reveal } from './Reveal'
import { CalendarIcon, CheckIcon, ClockIcon, SeatIcon, UsersIcon } from './icons'

const words = ['pottery', 'bookbinding', 'risograph', 'sourdough', 'weaving']

/** "Bookings for [word] workshops", with the word swapping in place. */
export function RotatingWord() {
  const index = useCycle(words.length, 2200)
  return (
    <p className="mt-5 text-xl font-medium text-emerald-100 sm:text-2xl">
      Bookings for{' '}
      <span
        key={index}
        className="animate-float-in inline-block rounded-lg bg-white/15 px-3 py-0.5 font-display font-bold text-emerald-200"
      >
        {words[index]}
      </span>{' '}
      workshops.
    </p>
  )
}

const stats = [
  { value: 100, suffix: '', label: 'seats per session, at most' },
  { value: 2, suffix: ' h', label: 'door check-in window' },
  { value: 0, suffix: '', label: 'seats ever overbooked' },
  { value: 1, suffix: ' tap', label: 'to cancel and free a seat' },
]

/** Four big numbers that count up when they scroll into view. */
export function StatsBand() {
  return (
    <section className="border-b border-muted/15">
      <dl className="mx-auto grid max-w-6xl grid-cols-2 gap-y-8 px-4 py-12 md:grid-cols-4">
        {stats.map((stat, index) => (
          <Reveal key={stat.label} delay={index * 100}>
            <div className="border-l-2 border-primary/30 pl-5">
              <dd className="font-display text-5xl font-bold tracking-tight text-primary-dark tabular-nums">
                <CountUp to={stat.value} suffix={stat.suffix} />
              </dd>
              <dt className="mt-1 text-sm text-muted">{stat.label}</dt>
            </div>
          </Reveal>
        ))}
      </dl>
    </section>
  )
}

type SeatState = 'taken' | 'waiting' | 'open' | 'in'

const seatTone: Record<SeatState, string> = {
  taken: 'bg-primary text-white',
  waiting: 'bg-emerald-200 text-emerald-950',
  open: 'border-2 border-dashed border-primary/40 bg-primary/5 text-primary',
  in: 'bg-primary-dark text-white',
}

interface Beat {
  who: string
  title: string
  body: string
  seat: SeatState
  waiting: boolean
}

// The capacity-1 story from the product spec, one beat at a time.
const beats: Beat[] = [
  { who: 'Host', title: 'Publishes a session', body: 'One seat, one evening. The room is open.', seat: 'open', waiting: false },
  { who: 'Guest A', title: 'Books the seat', body: 'Confirmed on the spot, no waiting for a reply.', seat: 'taken', waiting: false },
  { who: 'Guest B', title: 'Joins the waitlist', body: 'The room is full, so B queues at position 1.', seat: 'taken', waiting: true },
  { who: 'Guest A', title: 'Cancels', body: 'B is promoted automatically, in the same moment.', seat: 'taken', waiting: false },
  { who: 'Host', title: 'Checks B in', body: 'Check-in opens two hours before the start.', seat: 'in', waiting: false },
]

/** Walks through booking, waitlist, promotion and check-in; the current beat lights up in turn. */
export function PromotionStory() {
  const [ref, seen] = useInView<HTMLOListElement>(0.3)
  const active = useCycle(beats.length, 2000)

  return (
    <ol ref={ref} className="relative mt-12 grid gap-6 md:grid-cols-5">
      <div
        aria-hidden="true"
        className="absolute left-[10%] right-[10%] top-9 hidden h-0.5 rounded bg-primary/15 md:block"
      >
        <div
          className="h-full rounded bg-primary transition-all duration-700 ease-out"
          style={{ width: seen ? `${(active / (beats.length - 1)) * 100}%` : '0%' }}
        />
      </div>
      {beats.map((beat, index) => {
        const current = seen && index === active
        const done = seen && index < active
        return (
          <li
            key={index}
            style={{ transitionDelay: `${index * 90}ms` }}
            className={`relative text-center transition-all duration-700 ${
              seen ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
            }`}
          >
            <div
              className={`relative mx-auto grid h-[72px] w-[72px] place-items-center rounded-2xl border bg-card transition-all duration-500 ${
                current
                  ? 'scale-110 border-primary shadow-[var(--shadow-lift)]'
                  : 'border-muted/15 shadow-[var(--shadow-card)]'
              }`}
            >
              <span
                aria-hidden="true"
                className={`grid h-9 w-9 place-items-center rounded-lg transition-colors duration-500 ${seatTone[beat.seat]}`}
              >
                {beat.seat === 'in' ? <CheckIcon className="h-5 w-5" /> : <SeatIcon className="h-5 w-5" />}
              </span>
              {beat.waiting && (
                <span
                  aria-hidden="true"
                  className="absolute -right-2 -top-2 grid h-6 w-6 place-items-center rounded-full bg-emerald-200 text-[11px] font-bold text-emerald-950 shadow"
                >
                  1
                </span>
              )}
              {done && (
                <span
                  aria-hidden="true"
                  className="absolute -bottom-2 -right-2 grid h-5 w-5 place-items-center rounded-full bg-primary text-white"
                >
                  <CheckIcon className="h-3 w-3" />
                </span>
              )}
            </div>
            <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.18em] text-primary">
              {index + 1} · {beat.who}
            </p>
            <h3 className="mt-1 text-base font-semibold text-text">{beat.title}</h3>
            <p className="mx-auto mt-1 max-w-[16rem] text-sm text-muted">{beat.body}</p>
          </li>
        )
      })}
    </ol>
  )
}

/** Ten seats that fill one by one when scrolled into view. */
function FillingMeter() {
  const [ref, seen] = useInView<HTMLDivElement>(0.6)
  return (
    <div ref={ref} className="relative mt-8 flex items-center gap-2" aria-hidden="true">
      {Array.from({ length: 10 }).map((_, index) => (
        <span
          key={index}
          style={{ transitionDelay: seen ? `${index * 110}ms` : '0ms' }}
          className={`h-6 w-6 rounded-md transition-all duration-300 ${
            index < 9
              ? seen
                ? 'scale-100 bg-emerald-100/90'
                : 'scale-50 bg-white/20'
              : 'border-2 border-dashed border-white/70'
          }`}
        />
      ))}
      <span className="ml-2 text-sm font-semibold text-emerald-100">9 / 10</span>
    </div>
  )
}

const tile =
  'transition-all duration-300 hover:-translate-y-1 hover:shadow-[var(--shadow-lift)]'

/** A bento grid of what the product does. Every tile describes real behaviour. */
export function FeatureBento() {
  return (
    <div className="mt-10 grid gap-4 md:grid-cols-6">
      <Reveal className="md:col-span-3 md:row-span-2">
        <article className={`relative h-full overflow-hidden rounded-3xl bg-primary-dark p-7 text-white ${tile}`}>
          <div aria-hidden="true" className="bg-dotgrid pointer-events-none absolute inset-0 opacity-30" />
          <span className="relative grid h-11 w-11 place-items-center rounded-xl bg-white/15">
            <SeatIcon className="h-6 w-6" />
          </span>
          <h3 className="relative mt-6 font-display text-3xl font-bold">Never overbooked</h3>
          <p className="relative mt-3 max-w-md text-emerald-50/85">
            Every booking locks the session while it counts seats, so two people can never take the
            last one. The room never holds more guests than its capacity.
          </p>
          <FillingMeter />
        </article>
      </Reveal>

      <Reveal delay={100} className="md:col-span-3">
        <article className={`h-full rounded-3xl bg-emerald-100 p-6 text-emerald-950 ${tile}`}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-950/10">
            <UsersIcon className="h-5 w-5" />
          </span>
          <h3 className="mt-4 font-display text-2xl font-bold">A waitlist that works itself</h3>
          <p className="mt-2 text-emerald-950/80">
            When someone cancels, the longest-waiting guest gets the seat right away. No messages
            to send.
          </p>
        </article>
      </Reveal>

      <Reveal delay={200} className="md:col-span-2">
        <article className={`h-full rounded-3xl bg-emerald-50 p-6 text-emerald-950 ${tile}`}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-950/10">
            <ClockIcon className="h-5 w-5" />
          </span>
          <h3 className="mt-4 font-display text-xl font-bold">Door check-in</h3>
          <p className="mt-2 text-sm text-emerald-950/80">
            Tick guests off from two hours before the start until the session ends.
          </p>
        </article>
      </Reveal>

      <Reveal delay={300} className="md:col-span-1">
        <article className={`h-full rounded-3xl bg-emerald-200 p-6 text-emerald-950 ${tile}`}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-950/10">
            <CalendarIcon className="h-5 w-5" />
          </span>
          <h3 className="mt-4 font-display text-xl font-bold">1–100</h3>
          <p className="mt-2 text-sm text-emerald-950/80">seats per session.</p>
        </article>
      </Reveal>

      <Reveal delay={150} className="md:col-span-6">
        <article className={`rounded-3xl border border-muted/15 bg-card p-6 shadow-[var(--shadow-card)] ${tile}`}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-display text-2xl font-bold text-text">Guests see only what they need</h3>
              <p className="mt-1 max-w-2xl text-muted">
                Hosts see names on the roster, never email addresses. Guests see their own bookings
                and waitlist position, and nobody else&apos;s.
              </p>
            </div>
            <span className="inline-flex shrink-0 items-center gap-2 rounded-full bg-primary/10 px-4 py-2 text-sm font-semibold text-primary">
              <CheckIcon className="h-4 w-4" />
              Names only
            </span>
          </div>
        </article>
      </Reveal>
    </div>
  )
}

const faqs = [
  {
    q: 'Do guests need an account to book?',
    a: 'Anyone can browse sessions. To book a seat or join a waitlist, a guest signs in or creates an account.',
  },
  {
    q: 'What happens when someone cancels?',
    a: 'If the guest held a confirmed seat, the guest who has waited longest is promoted into it straight away, in the same step as the cancellation.',
  },
  {
    q: 'Can I edit a session after publishing it?',
    a: 'Not in this version. To change something, cancel the session and publish a new one. Cancelling cancels every pending booking on it.',
  },
  {
    q: 'When can I check guests in?',
    a: 'From two hours before the session starts until it ends. Only confirmed guests can be checked in, and a checked-in guest keeps their seat.',
  },
  {
    q: 'Who can see my email address?',
    a: 'Nobody but you. Hosts see display names on the roster, never email addresses.',
  },
]

/** Native disclosure widgets, so it works without JavaScript and with a keyboard. */
export function Faq() {
  return (
    <div className="mx-auto mt-10 max-w-3xl divide-y divide-muted/15 rounded-3xl border border-muted/15 bg-card shadow-[var(--shadow-card)]">
      {faqs.map((item) => (
        <details key={item.q} className="group px-6 py-5 [&_summary::-webkit-details-marker]:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-semibold text-text">
            {item.q}
            <span
              aria-hidden="true"
              className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary/10 text-primary transition-transform duration-300 group-open:rotate-45"
            >
              +
            </span>
          </summary>
          <p className="animate-float-in mt-3 text-muted">{item.a}</p>
        </details>
      ))}
    </div>
  )
}

/** The closing call to action. */
export function CtaBand() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-20">
      <Reveal>
        <div className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-emerald-950 via-primary-dark to-primary px-8 py-14 text-center text-white sm:px-14">
          <div aria-hidden="true" className="bg-dotgrid pointer-events-none absolute inset-0 opacity-25" />
          <div
            aria-hidden="true"
            className="animate-drift pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-emerald-300/25 blur-3xl"
          />
          <h2 className="relative text-4xl font-bold tracking-tight sm:text-5xl">Fill your next workshop.</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-emerald-50/85">
            Publish a session in a minute. Share the link. Watch the seats fill, and the waitlist
            take care of itself.
          </p>
          <div className="relative mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to={authHref('signup')}
              className="rounded-full bg-emerald-200 px-7 py-3 text-sm font-bold text-primary-dark shadow-lg transition-all hover:-translate-y-0.5 hover:bg-emerald-100"
            >
              Start hosting
            </Link>
            <Link
              to={authHref('login')}
              className="rounded-full border border-white/40 px-7 py-3 text-sm font-semibold transition-colors hover:bg-white/10"
            >
              Sign in
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  )
}
