import { Link } from 'react-router-dom'

export function SignupPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight text-text">Create account</h1>
      <p className="mt-4 max-w-xl text-muted">
        Registration is not available yet. Accounts arrive with the authentication milestone.
      </p>
      <p className="mt-6 text-sm text-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-primary hover:text-primary/80">
          Sign in
        </Link>
        .
      </p>
    </div>
  )
}
