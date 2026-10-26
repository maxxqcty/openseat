import { Link } from 'react-router-dom'

const steps = [
  {
    title: 'Publish a session',
    body: 'Set the time, place, and number of seats. No spreadsheets or group chats.',
  },
  {
    title: 'Take bookings',
    body: 'Guests reserve a seat, or join the waitlist when the session is full.',
  },
  {
    title: 'Fill every seat',
    body: 'Cancel a booking and the oldest waiting guest is promoted automatically.',
  },
]

export function LandingPage() {
  return (
    <>
      <section className="bg-primary text-surface">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-[0.3em] uppercase">Workshop bookings</p>
          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-6xl">OpenSeat</h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed">
            Fill every seat, without overbooking. One roster, one waitlist, and automatic promotion
            when someone cancels.
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Link
              to="/signup"
              className="inline-flex items-center justify-center rounded-md bg-surface px-5 py-3 font-semibold text-primary transition-colors hover:bg-surface/90"
            >
              Create account
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center justify-center rounded-md border border-surface/60 px-5 py-3 font-semibold text-surface transition-colors hover:bg-surface/10"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-2xl font-bold tracking-tight text-text">How it works</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          {steps.map((step) => (
            <article key={step.title} className="rounded-lg border border-muted/20 bg-surface p-6">
              <h3 className="text-base font-semibold text-text">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}
