import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight text-text">Page not found</h1>
      <p className="mt-4 max-w-xl text-muted">
        The page you are looking for does not exist or has moved.
      </p>
      <Link
        to="/"
        className="mt-8 inline-flex items-center justify-center rounded-md bg-primary px-5 py-3 font-semibold text-surface transition-colors hover:bg-primary/90"
      >
        Back to browse
      </Link>
    </div>
  )
}
