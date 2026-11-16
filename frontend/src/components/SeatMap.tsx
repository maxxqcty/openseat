import { useCycle } from '../lib/motion'
import { CheckIcon } from './icons'

const SEATS = 12
const FREED_SEAT = 4

// The loop tells the product's one story:
//   0  room is full, two guests waiting
//   1  a guest cancels, one seat frees up
//   2  the first waiting guest is promoted into it
//   3  the room is full again and a new guest joins the waitlist
const phases = [
  { taken: SEATS, promoting: false, queue: 2, chip: 'Room is full', note: '2 guests waiting' },
  { taken: SEATS - 1, promoting: false, queue: 2, chip: 'A guest cancelled', note: 'One seat just freed' },
  { taken: SEATS, promoting: true, queue: 1, chip: 'Guest promoted', note: 'Seat filled automatically' },
  { taken: SEATS, promoting: false, queue: 2, chip: 'New guest joined', note: 'Waitlist position 2' },
] as const

/** A small seat map that loops through cancel and promote. Static when motion is off. */
export function SeatMap() {
  const phase = useCycle(phases.length, 2400)
  const state = phases[phase]

  return (
    <div aria-hidden="true" className="relative mx-auto mb-14 w-full max-w-sm animate-float-in">
      <div className="rounded-3xl border border-white/15 bg-white/10 p-6 shadow-2xl backdrop-blur-sm">
        <div className="mb-5 flex items-center justify-between text-xs font-semibold text-white/80">
          <span>Risograph Printing · Room 2</span>
          <span className="rounded-full bg-white/15 px-2.5 py-1 tabular-nums">
            {state.taken} / {SEATS} seats
          </span>
        </div>

        <div className="grid grid-cols-6 gap-3">
          {Array.from({ length: SEATS }).map((_, index) => {
            const freed = index === FREED_SEAT
            const open = freed && phase === 1
            const promoted = freed && state.promoting
            return (
              <span
                key={index}
                className={`aspect-square rounded-lg transition-all duration-500 ${
                  open
                    ? 'animate-seat-pulse border-2 border-dashed border-white/80 bg-transparent'
                    : promoted
                      ? 'scale-110 bg-emerald-300 shadow-[0_0_0_4px_rgb(110_231_183_/_0.35)]'
                      : 'bg-emerald-100/90'
                }`}
              />
            )
          })}
        </div>

        <div className="mt-5 flex items-center gap-2 border-t border-white/15 pt-4">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-white/70">
            Waitlist
          </span>
          <div className="flex gap-2">
            {Array.from({ length: state.queue }).map((_, index) => (
              <span
                key={index}
                className="grid h-6 min-w-6 place-items-center rounded-full bg-emerald-300 px-1.5 text-[11px] font-bold text-emerald-950 transition-all duration-500"
              >
                {index + 1}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="absolute -right-6 -top-8 hidden xl:block">
        <div className="animate-bob rotate-6 overflow-hidden rounded-xl bg-emerald-100 text-primary-dark shadow-xl">
          <div className="flex">
            <span className="flex flex-col items-center justify-center bg-emerald-200 px-3 py-2 font-display leading-none">
              <span className="text-[10px] font-bold uppercase tracking-widest">Nov</span>
              <span className="text-2xl font-bold">23</span>
            </span>
            <span className="px-3 py-2 text-xs font-bold">
              Risograph
              <span className="block font-medium opacity-75">Admit one</span>
            </span>
          </div>
        </div>
      </div>

      <div
        key={phase}
        className="animate-float-in absolute -bottom-14 -left-4 flex items-center gap-3 rounded-2xl bg-card px-4 py-3 text-sm shadow-xl sm:-left-8"
      >
        <span className="grid h-8 w-8 place-items-center rounded-full bg-primary/10 text-primary">
          <CheckIcon className="h-4 w-4" />
        </span>
        <span className="text-text">
          <strong className="block font-semibold">{state.chip}</strong>
          <span className="text-xs text-muted">{state.note}</span>
        </span>
      </div>
    </div>
  )
}
