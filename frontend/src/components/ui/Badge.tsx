import type { ReactNode } from 'react'

type BadgeTone = 'neutral' | 'blue' | 'success'

type BadgeProps = {
  tone: BadgeTone
  children?: ReactNode
}

const toneClass: Record<BadgeTone, string> = {
  neutral:
    'text-rs-muted bg-rs-sky-2 border border-rs-line',
  blue: 'text-rs-blue bg-rs-sky border border-[#cfdcfb]',
  success: 'text-[#0d6f3e] bg-[#dcf5e3] border border-[#bce7c8]',
}

export function Badge({ tone, children }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 text-[10.5px] font-extrabold tracking-[0.05em] uppercase px-[11px] py-[5px] rounded-full',
        toneClass[tone],
      ].join(' ')}
    >
      {children}
    </span>
  )
}
