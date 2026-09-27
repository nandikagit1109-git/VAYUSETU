/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    // No shadow scale at all: surfaces are separated by tone + 1px hairlines, never drop shadows.
    boxShadow: { none: 'none' },
    // Small, deliberate radii (instrument/industrial feel). xl/2xl/3xl are intentionally absent
    // so the "same soft corner on every div" look cannot creep back in.
    borderRadius: {
      none: '0',
      sm: '2px',
      DEFAULT: '3px',
      md: '4px',
      lg: '6px',
      full: '9999px',
    },
    extend: {
      colors: {
        haze: 'var(--haze)',
        panel: 'var(--panel)',
        soot: 'var(--soot)',
        ash: 'var(--ash)',
        ochre: 'var(--ochre)',
        ember: 'var(--ember)',
        hairline: 'var(--hairline)',
        'hairline-strong': 'var(--hairline-strong)',
        'sev-moderate': 'var(--sev-moderate)',
        'sev-poor': 'var(--sev-poor)',
        'sev-very-poor': 'var(--sev-very-poor)',
        'sev-severe': 'var(--sev-severe)',
      },
      fontFamily: {
        display: ['Bricolage Grotesque', 'IBM Plex Sans', 'sans-serif'],
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
