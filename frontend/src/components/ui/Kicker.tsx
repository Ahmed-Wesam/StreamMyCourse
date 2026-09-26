import type { ReactNode } from 'react'

type KickerProps = {
  children?: ReactNode
}

export function Kicker({ children }: KickerProps) {
  return (
    <span className="block text-center text-rs-blue font-bold text-[13px] tracking-[0.12em] uppercase mb-[14px]">
      {children}
    </span>
  )
}
