import type { ReactNode } from 'react'

type StrokeIconProps = {
  strokeWidth?: number
}

function StrokeIcon({ strokeWidth = 2, children }: StrokeIconProps & { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  )
}

export function IconArrow({ strokeWidth = 2.5 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </StrokeIcon>
  )
}

export function IconChevron() {
  return (
    <StrokeIcon strokeWidth={2.4}>
      <path d="m9 18 6-6-6-6" />
    </StrokeIcon>
  )
}

export function IconBook({ strokeWidth = 2 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </StrokeIcon>
  )
}

export function IconTrend() {
  return (
    <StrokeIcon strokeWidth={2}>
      <path d="M3 3v18h18" />
      <path d="m7 14 3-3 3 2 4-5" />
    </StrokeIcon>
  )
}

export function IconMedal({ strokeWidth = 2 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <circle cx="12" cy="8" r="6" />
      <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
    </StrokeIcon>
  )
}

export function IconPeople({ strokeWidth = 2 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </StrokeIcon>
  )
}

export function IconClipboard({ strokeWidth = 1.9 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
    </StrokeIcon>
  )
}

export function IconBars({ strokeWidth = 1.9 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M3 3v18h18" />
      <rect x="7" y="13" width="3" height="5" rx="1" />
      <rect x="12" y="9" width="3" height="9" rx="1" />
      <rect x="17" y="5" width="3" height="13" rx="1" />
    </StrokeIcon>
  )
}

export function IconPen({ strokeWidth = 1.9 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </StrokeIcon>
  )
}

export function IconSearch({ strokeWidth = 1.9 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </StrokeIcon>
  )
}

export function IconCheck({ strokeWidth = 2.6 }: StrokeIconProps) {
  return (
    <StrokeIcon strokeWidth={strokeWidth}>
      <path d="M20 6 9 17l-5-5" />
    </StrokeIcon>
  )
}

export function IconLock() {
  return (
    <StrokeIcon strokeWidth={2}>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </StrokeIcon>
  )
}

export function IconGear() {
  return (
    <StrokeIcon strokeWidth={2}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </StrokeIcon>
  )
}

export function IconChat() {
  return (
    <StrokeIcon strokeWidth={2}>
      <path d="M21 11.5a8.38 8.38 0 0 1-9 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.2A8.5 8.5 0 1 1 21 11.5z" />
    </StrokeIcon>
  )
}

export function IconFlame() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M13.5 0c.5 4-2 5.5-3.5 7.5C8 10 7 12 7.2 14.5 7.5 18 10 21 13.5 21c4 0 7-3.4 7-7.6 0-3.2-2.2-5.6-4-7-.3 1.6-1 2.6-2 2.6-2 0-.8-3-1-9z" />
    </svg>
  )
}

export function IconStar() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: 11, height: 11 }}>
      <path d="M12 2l2.4 7.4H22l-6 4.4 2.3 7.2L12 16.6 5.7 21l2.3-7.2-6-4.4h7.6z" />
    </svg>
  )
}

export function CourseGlyph({ title, strokeWidth = 1.9 }: { title: string; strokeWidth?: number }) {
  const name = title.toLowerCase()
  if (name.includes('statistic')) return <IconBars strokeWidth={strokeWidth} />
  if (name.includes('writing')) return <IconPen strokeWidth={strokeWidth} />
  if (name.includes('systematic') || name.includes('meta')) return <IconSearch strokeWidth={strokeWidth} />
  return <IconClipboard strokeWidth={strokeWidth} />
}
