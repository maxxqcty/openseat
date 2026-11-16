import type { ReactNode } from 'react'

export interface EmptyStateProps {
  title: string
  message: string
  action?: ReactNode
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <section className="mt-6 rounded-2xl border-2 border-dashed border-muted/25 bg-card/60 p-10 text-center">
      <h2 className="text-lg font-semibold text-text">{title}</h2>
      <p className="mt-2 text-sm text-muted">{message}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </section>
  )
}
