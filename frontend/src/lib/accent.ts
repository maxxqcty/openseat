/**
 * Two greens, so neighbouring tickets alternate gently without the page turning
 * into a rainbow. The accent is derived from the session id, so a session looks
 * the same on every page and visit.
 * Class names are written out in full so Tailwind can see them.
 */
export interface Accent {
  /** Solid colour for ticket stubs and filled seats. */
  stub: string
  /** Text colour that stays readable on `stub`. */
  onStub: string
  /** Pale tint for panels and empty seats. */
  soft: string
  /** Readable text colour on `soft`. */
  text: string
  /** Colour of a filled seat dot. */
  dot: string
  /** Border colour that matches the tint. */
  border: string
}

const accents: Accent[] = [
  {
    stub: 'bg-emerald-700',
    onStub: 'text-white',
    soft: 'bg-emerald-50',
    text: 'text-emerald-800',
    dot: 'bg-emerald-600',
    border: 'border-emerald-200',
  },
  {
    stub: 'bg-emerald-900',
    onStub: 'text-white',
    soft: 'bg-emerald-50',
    text: 'text-emerald-900',
    dot: 'bg-emerald-800',
    border: 'border-emerald-200',
  },
]

export function accentFor(id: string): Accent {
  let hash = 0
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  }
  return accents[hash % accents.length]
}
