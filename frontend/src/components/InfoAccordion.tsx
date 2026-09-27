import { useState } from 'react'
import type { ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

interface Props {
  title: string
  children: ReactNode
}

// Narrow explanatory disclosure (not a marketing FAQ): real product mechanics
// most people have not met before, e.g. what federated learning or GRAP means.
export default function InfoAccordion({ title, children }: Props) {
  const [open, setOpen] = useState(false)
  const reduced = useReducedMotion()
  const dur = reduced ? 0 : 0.35

  return (
    <div className="rounded-sm border border-hairline bg-haze">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-medium text-soot"
      >
        {title}
        <motion.svg
          viewBox="0 0 16 16"
          width="14"
          height="14"
          aria-hidden="true"
          className="shrink-0 text-ash"
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: dur }}
        >
          <path d="M3 6l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: dur, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 text-xs leading-relaxed text-ash">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
