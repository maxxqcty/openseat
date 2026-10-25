import type { ButtonHTMLAttributes } from 'react'

const variantClasses = {
  primary: 'bg-primary text-surface hover:bg-primary/90',
  secondary: 'border border-muted/30 bg-surface text-text hover:bg-muted/10',
  danger: 'bg-danger text-surface hover:bg-danger/90',
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
      className={`inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${variantClasses[variant]} ${className}`.trim()}
      {...props}
    />
  )
}
