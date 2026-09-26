import type { ReactNode } from 'react'

type EyebrowProps = {
  children?: ReactNode
}

export function Eyebrow({ children }: EyebrowProps) {
  return (
    <span className="inline-flex items-center gap-[9px] text-[13px] font-bold tracking-wider uppercase text-rs-blue bg-rs-sky px-4 py-2 rounded-full border border-[#dbe6ff]">
      <span aria-hidden className="size-[7px] rounded-full bg-rs-grad-cta shrink-0" />
      {children}
    </span>
  )
}
