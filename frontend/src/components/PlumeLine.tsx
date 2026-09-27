import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { EASE } from '../motion'

const X0 = 8
const X1 = 292
const Y_MID = 22
const AMP = 6
const REFLECT_MID = 42

function sineY(x: number, mid: number, flip = 1): number {
  return mid + flip * AMP * Math.sin(x / 22)
}

function buildPath(mid: number, flip = 1): string {
  const parts: string[] = []
  const n = 56
  for (let i = 0; i <= n; i++) {
    const x = X0 + (i / n) * (X1 - X0)
    parts.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${sineY(x, mid, flip).toFixed(1)}`)
  }
  return parts.join(' ')
}

const MAIN_D = buildPath(Y_MID)
const REFLECT_D = buildPath(REFLECT_MID, -1)

interface Props {
  value: string
  complete: boolean
}

// The signature interaction: a wisp-of-smoke line that advances as the person
// types their city, pulses at the tip when they pause, retracts on backspace,
// and settles with a faint mirrored reflection once a valid city is chosen.
export default function PlumeLine({ value, complete }: Props) {
  const reduced = useReducedMotion()
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    setPaused(false)
    if (!value) return
    const t = window.setTimeout(() => setPaused(true), 2000)
    return () => window.clearTimeout(t)
  }, [value])

  const progress = Math.min(value.trim().length / 8, 1)
  const tipX = X0 + progress * (X1 - X0)
  const tipY = sineY(tipX, Y_MID)
  const pulsing = paused && !complete && value.trim().length > 0 && !reduced

  return (
    <svg viewBox="0 0 300 56" width="100%" height="56" aria-hidden="true" fill="none" className="block">
      {/* Main drifting wisp; pathLength tracks typing progress so it advances and retracts. */}
      <motion.path
        d={MAIN_D}
        stroke="var(--ochre)"
        strokeWidth={2}
        strokeLinecap="round"
        initial={false}
        animate={{ pathLength: progress }}
        transition={reduced ? { duration: 0 } : { duration: 0.35, ease: EASE }}
      />
      {/* Fainter mirrored reflection, revealed only once a valid city settles the line. */}
      <motion.path
        d={REFLECT_D}
        stroke="var(--ochre)"
        strokeWidth={1.5}
        strokeLinecap="round"
        initial={false}
        animate={{ pathLength: complete ? progress : 0, opacity: complete ? 0.32 : 0 }}
        transition={reduced ? { duration: 0 } : { duration: 0.6, ease: EASE }}
      />
      {/* Leading tip: pulses only after a 2s pause, still otherwise. */}
      <motion.circle
        cx={tipX}
        cy={tipY}
        r={3}
        fill="var(--ember)"
        style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
        animate={pulsing ? { scale: [1, 1.15, 1] } : { scale: 1 }}
        transition={pulsing ? { duration: 1.2, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.2 }}
      />
    </svg>
  )
}
