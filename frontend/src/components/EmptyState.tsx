import type { ReactNode } from 'react'

export interface EmptyStateProps {
  title: string
  message: string
  action?: ReactNode
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <section className="rounded-lg border border-muted/20 bg-surface p-8 text-center">
      <h2 className="text-lg font-semibold text-text">{title}</h2>
      <p className="mt-2 text-sm text-muted">{message}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </section>
  )
}
