import type { CSSProperties, ReactNode } from 'react'

export function RtIcon({
  strokeWidth = 2,
  style,
  children,
}: {
  strokeWidth?: number | string
  style?: CSSProperties
  children: ReactNode
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
    >
      {children}
    </svg>
  )
}

export function ArrowIcon() {
  return (
    <RtIcon strokeWidth="2.5">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </RtIcon>
  )
}

export function PlusIcon() {
  return (
    <RtIcon strokeWidth="2.5">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </RtIcon>
  )
}

export function CheckIcon({ strokeWidth = 2.6 }: { strokeWidth?: number | string }) {
  return (
    <RtIcon strokeWidth={strokeWidth}>
      <path d="M20 6 9 17l-5-5" />
    </RtIcon>
  )
}
