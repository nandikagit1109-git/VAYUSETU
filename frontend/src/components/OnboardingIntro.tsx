import { useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { DUR, EASE } from '../motion'

const SOOT = '#211e1a'
const OCHRE = '#b0763a'
const EMBER = '#9e3b18'
const ASH = '#7c7367'

const INTRO_KEY = 'vayusetu.introSeen'
// Long enough to read the beat copy at a normal pace before it moves on.
const BEAT_MS = 4800

interface Beat {
  eyebrow: string
  title: string
  body: string
  art: (reduced: boolean) => ReactElement
}

// Each beat reuses the SmokePath draw-in so the intro rhymes with the plume line
// the user meets in the report form immediately afterwards.
function PinArt({ reduced }: { reduced: boolean }) {
  return (
    <svg viewBox="0 0 140 64" width="140" height="64" aria-hidden="true" fill="none">
      <motion.path
        d="M6 50C26 50 30 34 52 34S80 20 100 20"
        stroke={OCHRE}
        strokeWidth={2}
        strokeLinecap="round"
        initial={{ pathLength: reduced ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={reduced ? { duration: 0 } : { duration: 1, ease: EASE }}
      />
      <motion.path
        d="M116 52c-6.4-7.8-9.4-12.2-9.4-16.4a9.4 9.4 0 1 1 18.8 0c0 4.2-3 8.6-9.4 16.4z"
        stroke={SOOT}
        strokeWidth={1.8}
        strokeLinejoin="round"
        initial={{ pathLength: reduced ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={reduced ? { duration: 0 } : { duration: 0.7, ease: EASE, delay: 0.55 }}
      />
      <motion.circle
        cx="116"
        cy="35.4"
        r="3"
        fill={EMBER}
        initial={{ opacity: reduced ? 1 : 0 }}
        animate={{ opacity: 1 }}
        transition={reduced ? { duration: 0 } : { duration: 0.3, delay: 1.1 }}
      />
    </svg>
  )
}

function NodesArt({ reduced }: { reduced: boolean }) {
  const locals = [
    { y: 14, delay: 0 },
    { y: 34, delay: 0.25 },
    { y: 54, delay: 0.5 },
  ]
  return (
    <svg viewBox="0 0 140 64" width="140" height="64" aria-hidden="true" fill="none">
      {locals.map((n) => (
        <motion.path
          key={n.y}
          d={`M26 ${n.y}C56 ${n.y} 62 34 96 34`}
          stroke={ASH}
          strokeWidth={1.6}
          strokeDasharray="5 4"
          initial={{ pathLength: reduced ? 1 : 0 }}
          animate={{ pathLength: 1 }}
          transition={reduced ? { duration: 0 } : { duration: 0.8, ease: EASE, delay: n.delay }}
        />
      ))}
      {locals.map((n) => (
        <circle key={`c${n.y}`} cx="22" cy={n.y} r="5" stroke={SOOT} strokeWidth={1.6} fill="#f2eee6" />
      ))}
      <motion.circle
        cx="104"
        cy="34"
        r="9"
        stroke={EMBER}
        strokeWidth={2.4}
        fill="#f2eee6"
        initial={{ opacity: reduced ? 1 : 0, scale: reduced ? 1 : 0.7 }}
        animate={{ opacity: 1, scale: 1 }}
        style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
        transition={reduced ? { duration: 0 } : { duration: 0.5, ease: EASE, delay: 1.3 }}
      />
    </svg>
  )
}

function WindArt({ reduced }: { reduced: boolean }) {
  return (
    <svg viewBox="0 0 140 64" width="140" height="64" aria-hidden="true" fill="none">
      <circle cx="18" cy="40" r="6" fill={EMBER} stroke={SOOT} strokeWidth={1.2} />
      <motion.path
        d="M26 40H96"
        stroke={OCHRE}
        strokeWidth={2}
        strokeDasharray="6 6"
        initial={{ pathLength: reduced ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={reduced ? { duration: 0 } : { duration: 1.1, ease: EASE, delay: 0.2 }}
      />
      <motion.path
        d="M96 32l10 8-10 8"
        stroke={SOOT}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: reduced ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={reduced ? { duration: 0 } : { duration: 0.4, ease: EASE, delay: 1.1 }}
      />
      <circle cx="122" cy="40" r="7" stroke={SOOT} strokeWidth={2} fill="#f2eee6" />
    </svg>
  )
}

const BEATS: Beat[] = [
  {
    eyebrow: 'Step 1 of 3',
    title: 'Report what the sky looks like',
    body: 'A photo or a visibility guess from your street turns into a haze score with a confidence value, pinned to the corridor map.',
    art: (reduced) => <PinArt reduced={reduced} />,
  },
  {
    eyebrow: 'Step 2 of 3',
    title: 'Three cities train together, data stays put',
    body: 'Delhi, Kanpur and Pune each train on their own observations. Only model weights travel; the raw reports never leave their city.',
    art: (reduced) => <NodesArt reduced={reduced} />,
  },
  {
    eyebrow: 'Step 3 of 3',
    title: 'The wind decides who breathes it',
    body: 'Hotspots are joined to the city downwind of them, with a travel time and the matching GRAP stage when a threshold is crossed.',
    art: (reduced) => <WindArt reduced={reduced} />,
  },
]

interface OnboardingIntroProps {
  onDone: () => void
}

export function hasSeenIntro(): boolean {
  try {
    return window.localStorage.getItem(INTRO_KEY) === '1'
  } catch {
    return true // storage blocked: do not trap the user in an intro they cannot dismiss
  }
}

export default function OnboardingIntro({ onDone }: OnboardingIntroProps) {
  const reduced = useReducedMotion()
  const [i, setI] = useState(0)

  // Auto-advance is a motion-driven behaviour, so it is off under reduced motion;
  // the beats stay reachable through the Next control instead.
  useEffect(() => {
    if (reduced) return
    const t = window.setTimeout(() => setI((prev) => Math.min(BEATS.length - 1, prev + 1)), BEAT_MS)
    return () => window.clearTimeout(t)
  }, [i, reduced])

  function finish() {
    try {
      window.localStorage.setItem(INTRO_KEY, '1')
    } catch {
      // ignore: the intro simply shows again next load
    }
    onDone()
  }

  const last = i === BEATS.length - 1

  return (
    <motion.div
      className="fixed inset-0 z-[1300] flex items-center justify-center p-6"
      style={{ background: 'rgba(33,30,26,0.55)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: reduced ? 0 : 0.3, ease: EASE }}
      role="dialog"
      aria-modal="true"
      aria-label="Welcome to VayuSetu"
    >
      <div className="w-full max-w-lg border border-hairline-strong bg-panel p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={i}
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: 18 }}
            transition={{ duration: reduced ? 0 : DUR, ease: EASE }}
          >
            <p className="label">{BEATS[i].eyebrow}</p>
            <h2 className="mt-2 font-display text-xl font-bold leading-snug text-soot">{BEATS[i].title}</h2>
            <p className="measure mt-2 text-sm leading-relaxed text-ash">{BEATS[i].body}</p>
            <div className="mt-5">{BEATS[i].art(Boolean(reduced))}</div>
          </motion.div>
        </AnimatePresence>

        <div className="mt-6 flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5" aria-hidden="true">
            {BEATS.map((b, idx) => (
              <span
                key={b.title}
                className="h-[3px] w-6"
                style={{ background: idx === i ? OCHRE : 'rgba(33,30,26,0.18)' }}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-quiet" onClick={finish}>
              Skip
            </button>
            {!last && (
              <button type="button" className="btn-quiet" onClick={() => setI((p) => p + 1)}>
                Next
              </button>
            )}
            <button type="button" className="btn-primary" onClick={last ? finish : () => setI((p) => p + 1)}>
              {last ? 'Start exploring' : 'Continue'}
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
