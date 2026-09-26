import type { HTMLAttributes, ReactNode } from 'react'

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children?: ReactNode
  className?: string
}

export function Card({ children, className, ...rest }: CardProps) {
  return (
    <div
      {...rest}
      className={['bg-white border border-rs-line rounded-rs shadow-rs', className]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}
