import type { ReactNode, SVGProps } from 'react'

type MarkProps = SVGProps<SVGSVGElement> & { sw?: string }

function Mark({ sw = '2', children, ...rest }: MarkProps & { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" {...rest}>
      {children}
    </svg>
  )
}

export function Chevron() {
  return (
    <Mark sw="2.2">
      <path d="m9 18 6-6-6-6" />
    </Mark>
  )
}

export function Arrow() {
  return (
    <Mark sw="2.5">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Mark>
  )
}

export function DollarIcon({ sw = '2' }: { sw?: string }) {
  return (
    <Mark sw={sw}>
      <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </Mark>
  )
}

export function ClockIcon() {
  return (
    <Mark sw="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </Mark>
  )
}

export function ChartIcon() {
  return (
    <Mark sw="2">
      <path d="M3 3v18h18" />
      <path d="m7 14 3-3 3 2 4-5" />
    </Mark>
  )
}

export function ShieldIcon({ sw = '2' }: { sw?: string }) {
  return (
    <Mark sw={sw}>
      <path d="M12 2 4 5v6c0 5 3.5 8.5 8 11 4.5-2.5 8-6 8-11V5z" />
    </Mark>
  )
}

export function MedalIcon({ sw = '2' }: { sw?: string }) {
  return (
    <Mark sw={sw}>
      <circle cx="12" cy="8" r="6" />
      <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
    </Mark>
  )
}

export function CheckIcon({ sw = '2.6' }: { sw?: string }) {
  return (
    <Mark sw={sw}>
      <path d="M20 6 9 17l-5-5" />
    </Mark>
  )
}

export function CrossIcon() {
  return (
    <Mark sw="2.4">
      <path d="M18 6 6 18M6 6l12 12" />
    </Mark>
  )
}

export function ChevronDown() {
  return (
    <Mark sw="2.4">
      <path d="m6 9 6 6 6-6" />
    </Mark>
  )
}

export function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2l2.4 7.4H22l-6 4.4 2.3 7.2L12 16.6 5.7 21l2.3-7.2-6-4.4h7.6z" />
    </svg>
  )
}

export function ModulesIcon() {
  return (
    <Mark sw="2">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18" />
    </Mark>
  )
}

export function LessonsIcon() {
  return (
    <Mark sw="2">
      <path d="M4 6h16M4 12h16M4 18h12" />
    </Mark>
  )
}

function Glyph({ sw = '1.9', children }: { sw?: string; children: ReactNode }) {
  return <Mark sw={sw}>{children}</Mark>
}

function questionGlyph() {
  return (
    <Glyph>
      <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3" />
      <path d="M12 17h.01" />
      <circle cx="12" cy="12" r="10" />
    </Glyph>
  )
}

const OWN: Record<string, () => ReactNode> = {
  question: questionGlyph,
  trend: () => (
    <Glyph>
      <path d="M3 3v18h18" />
      <path d="m7 14 3-3 3 2 4-5" />
    </Glyph>
  ),
  form: () => (
    <Glyph>
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </Glyph>
  ),
  bars: () => (
    <Glyph>
      <path d="M3 3v18h18" />
      <rect x="7" y="13" width="3" height="5" rx="1" />
      <rect x="12" y="9" width="3" height="9" rx="1" />
      <rect x="17" y="5" width="3" height="13" rx="1" />
    </Glyph>
  ),
  table: () => (
    <Glyph>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18" />
    </Glyph>
  ),
  rewind: () => (
    <Glyph>
      <path d="M21 12a9 9 0 1 1-3-6.7" />
      <path d="M21 5v4h-4" />
    </Glyph>
  ),
  pulse: () => (
    <Glyph>
      <path d="M3 12h4l3-8 4 16 3-8h4" />
    </Glyph>
  ),
  calendar: () => (
    <Glyph>
      <path d="M9 3v4M15 3v4M4 9h16" />
      <rect x="4" y="5" width="16" height="16" rx="2" />
      <path d="m9 14 2 2 4-4" />
    </Glyph>
  ),
  database: () => (
    <Glyph>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
    </Glyph>
  ),
  download: () => (
    <Glyph>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </Glyph>
  ),
  bulb: () => (
    <Glyph>
      <path d="M12 3v3M5.5 5.5l2 2M3 12h3M21 12h-3M16.5 7.5l2-2" />
      <path d="M9 17a3 3 0 0 1 6 0v3H9z" />
    </Glyph>
  ),
  book: () => (
    <Glyph>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </Glyph>
  ),
  doc: () => (
    <Glyph>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M8 13h8M8 17h5" />
    </Glyph>
  ),
  pen: () => (
    <Glyph>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </Glyph>
  ),
  search: () => (
    <Glyph>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </Glyph>
  ),
  screen: () => (
    <Glyph>
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="m9 11 2 2 4-4" />
    </Glyph>
  ),
  people: () => (
    <Glyph>
      <path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
      <path d="M2 21a7 7 0 0 1 14 0" />
      <path d="M19 8v6M16 11h6" />
    </Glyph>
  ),
  shieldCheck: () => (
    <Glyph>
      <path d="M12 2 4 5v6c0 5 3.5 8.5 8 11 4.5-2.5 8-6 8-11V5z" />
      <path d="m9 12 2 2 4-4" />
    </Glyph>
  ),
  file: () => (
    <Glyph>
      <path d="M6 2h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z" />
      <path d="M14 2v5h5M9 13h6M9 17h4" />
    </Glyph>
  ),
  eye: () => (
    <Glyph>
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </Glyph>
  ),
  grid: () => (
    <Glyph>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18M9 4v16" />
    </Glyph>
  ),
  warn: () => (
    <Glyph>
      <path d="M12 9v4M12 17h.01" />
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
    </Glyph>
  ),
  clipboard: () => (
    <Glyph>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
    </Glyph>
  ),
  team: () => (
    <Glyph>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </Glyph>
  ),
}

export function OwnGlyph({ name }: { name: string }) {
  const draw = OWN[name] ?? questionGlyph
  return draw()
}

export const HANDS_ON_GLYPHS: Record<string, readonly string[]> = {
  methodology: ['question', 'trend', 'form', 'bars'],
  statistics: ['database', 'download', 'trend', 'bulb'],
  writing: ['book', 'doc', 'bars', 'pen'],
  srma: ['question', 'search', 'screen', 'doc'],
}

export const HIGHLIGHT_GLYPHS: Record<string, readonly string[]> = {
  methodology: ['question', 'trend', 'people', 'pen', 'shieldCheck', 'file'],
  statistics: ['eye', 'grid', 'bars', 'pen', 'warn', 'file'],
}

export const JOURNEY_GLYPHS = ['clipboard', 'bars', 'pen', 'search', 'team'] as const
