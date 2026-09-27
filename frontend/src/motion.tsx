import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

// The single approved easing + drift for every enter/exit in the app.
export const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]
export const DRIFT = 18
export const DUR = 0.6

interface FadeUpProps {
  children: ReactNode
  delay?: number
  className?: string
}

// Fade in + 18px upward drift, for section content appearing for the first time.
export function FadeUp({ children, delay = 0, className }: FadeUpProps) {
  const reduced = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: DRIFT }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduced ? { duration: 0 } : { duration: DUR, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  )
}

interface RevealWordsProps {
  text: string
  className?: string
  stagger?: number
  delay?: number
}

// Word-by-word reveal, reserved for genuinely explanatory paragraphs.
export function RevealWords({ text, className, stagger = 0.05, delay = 0 }: RevealWordsProps) {
  const reduced = useReducedMotion()
  const words = text.split(' ')
  return (
    <span className={className} aria-label={text}>
      {words.map((w, i) => (
        <motion.span
          key={`${w}-${i}`}
          aria-hidden="true"
          className="inline-block"
          initial={reduced ? { opacity: 1 } : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={reduced ? { duration: 0 } : { duration: 0.35, ease: EASE, delay: delay + i * stagger }}
        >
          {w}
          {i < words.length - 1 ? ' ' : ''}
        </motion.span>
      ))}
    </span>
  )
}

interface SmokePathProps {
  d: string
  viewBox?: string
  width?: number | string
  height?: number | string
  stroke?: string
  strokeWidth?: number
  duration?: number
  delay?: number
  opacity?: number
  className?: string
}

// The project's draw-in primitive: an SVG path that draws itself in.
// Used for the plume line, wind vectors, intro illustrations and chart rhyming.
export function SmokePath({
  d,
  viewBox = '0 0 100 100',
  width = '100%',
  height = '100%',
  stroke = 'var(--ochre)',
  strokeWidth = 2,
  duration = 1.1,
  delay = 0,
  opacity = 1,
  className,
}: SmokePathProps) {
  const reduced = useReducedMotion()
  return (
    <svg viewBox={viewBox} width={width} height={height} className={className} aria-hidden="true" fill="none">
      <motion.path
        d={d}
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        initial={{ pathLength: reduced ? 1 : 0, opacity }}
        animate={{ pathLength: 1, opacity }}
        transition={reduced ? { duration: 0 } : { duration, ease: EASE, delay }}
      />
    </svg>
  )
}

interface SmokeRuleProps {
  className?: string
  delay?: number
}

// Horizontal divider that draws in from the left instead of simply appearing.
export function SmokeRule({ className = '', delay = 0 }: SmokeRuleProps) {
  const reduced = useReducedMotion()
  return (
    <motion.div
      aria-hidden="true"
      className={className}
      style={{ height: 1, background: 'var(--hairline-strong)', transformOrigin: 'left center' }}
      initial={{ scaleX: reduced ? 1 : 0 }}
      animate={{ scaleX: 1 }}
      transition={reduced ? { duration: 0 } : { duration: DUR, ease: EASE, delay }}
    />
  )
}
