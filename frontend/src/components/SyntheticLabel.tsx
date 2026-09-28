import { useMeta } from '../hooks'

// The persistent, quiet honesty label (section 2): shown whenever
// /api/meta reports data_mode=synthetic. Never claims the numbers are real.
export default function SyntheticLabel() {
  const meta = useMeta()
  if (!meta || meta.data_mode !== 'synthetic') return null
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-sm border border-hairline bg-haze px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] text-ash"
      title="All observations in this demo are generated from a seeded synthetic model. They are not real measurements."
    >
      Synthetic demonstration data
    </span>
  )
}
