import type { CourseSealKey } from './courseCertificateMeta'

type CourseSealIconProps = {
  sealKey: CourseSealKey | null
  variant: 'earned' | 'locked'
}

function SealGraphic({ sealKey }: { sealKey: CourseSealKey | null }) {
  switch (sealKey) {
    case 'statistics-spss':
      return (
        <>
          <path d="M3 3v18h18" />
          <rect x="7" y="13" width="3" height="5" rx="1" />
          <rect x="12" y="9" width="3" height="9" rx="1" />
          <rect x="17" y="5" width="3" height="13" rx="1" />
        </>
      )
    case 'scientific-writing':
      return (
        <>
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
        </>
      )
    case 'systematic-reviews-meta-analysis':
      return (
        <>
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </>
      )
    case 'research-methodology':
    default:
      return (
        <>
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
          <rect x="9" y="3" width="6" height="4" rx="1" />
        </>
      )
  }
}

export function CourseSealIcon({ sealKey, variant }: CourseSealIconProps) {
  const className = variant === 'earned' ? 'cf-seal' : 'cl-seal'
  const stroke = variant === 'earned' ? 1.9 : 2

  return (
    <div className={className}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
        style={variant === 'locked' ? { width: 28, height: 28 } : undefined}
      >
        <SealGraphic sealKey={sealKey} />
      </svg>
    </div>
  )
}
