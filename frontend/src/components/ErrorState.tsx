import type { ReactNode } from 'react'

export interface ErrorStateProps {
  title: string
  message: string
  action?: ReactNode
}

export function ErrorState({ title, message, action }: ErrorStateProps) {
  return (
    <section
      role="alert"
      className="rounded-lg border border-danger/30 bg-danger/5 p-8 text-center"
    >
      <h2 className="text-lg font-semibold text-text">{title}</h2>
      <p className="mt-2 text-sm text-muted">{message}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </section>
  )
}
