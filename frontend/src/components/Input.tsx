import { useId, type InputHTMLAttributes } from 'react'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function Input({ label, error, id, className = '', ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const errorId = `${inputId}-error`

  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-medium text-text">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error ? errorId : undefined}
        className={`block w-full rounded-md border border-muted/30 bg-surface px-3 py-2 text-sm text-text placeholder:text-muted/70 ${className}`.trim()}
        {...props}
      />
      {error && (
        <p id={errorId} className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
