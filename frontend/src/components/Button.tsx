import type { ButtonHTMLAttributes } from 'react'

const variantClasses = {
  primary: 'bg-primary text-surface shadow-sm hover:bg-primary-dark hover:shadow-md',
  secondary:
    'border border-muted/25 bg-card text-text shadow-sm hover:border-primary/40 hover:bg-primary/5',
  danger: 'bg-danger text-surface shadow-sm hover:bg-danger/90',
} as const

export type ButtonVariant = keyof typeof variantClasses

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

export function Button({
  variant = 'primary',
  className = '',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition-all active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60 ${variantClasses[variant]} ${className}`.trim()}
      {...props}
    />
  )
}
