import { Link } from 'react-router-dom'

export function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <p className="text-sm font-semibold tracking-[0.3em] text-emerald-400 uppercase">
          Workshop bookings
        </p>
        <h1 className="mt-4 text-5xl font-bold tracking-tight sm:text-6xl">OpenSeat</h1>
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">
          Fill every seat, without overbooking. Publish a session, take bookings, and let the
          waitlist promote the next guest automatically.
        </p>
        <div className="mt-10">
          <Link
            className="inline-flex items-center rounded-md bg-emerald-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-emerald-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-300"
            to="/login"
          >
            Sign in
          </Link>
        </div>
      </div>
    </main>
  )
}
