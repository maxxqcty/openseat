import { Link } from 'react-router-dom'

export function LoginPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <p className="text-sm font-semibold tracking-[0.3em] text-emerald-400 uppercase">
          OpenSeat
        </p>
        <h1 className="mt-4 text-4xl font-bold tracking-tight">Sign in</h1>
        <p className="mt-4 max-w-xl text-slate-300">
          Accounts and authentication are not available yet. This page is a placeholder for the next
          milestone.
        </p>
        <div className="mt-8">
          <Link className="font-semibold text-emerald-400 hover:text-emerald-300" to="/">
            Back to OpenSeat
          </Link>
        </div>
      </div>
    </main>
  )
}
