import { useEffect, useRef, useState, type ReactNode } from 'react'

type RevealProps = {
  children?: ReactNode
  className?: string
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function shouldShowImmediately(): boolean {
  if (typeof window === 'undefined') return false
  if (prefersReducedMotion()) return true
  if (typeof window.IntersectionObserver === 'undefined') return true
  return false
}

export function Reveal({ children, className }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(shouldShowImmediately)

  useEffect(() => {
    if (visible) return

    if (shouldShowImmediately()) {
      setVisible(true)
      return
    }

    const node = ref.current
    if (!node) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    observer.observe(node)
    return () => {
      observer.disconnect()
    }
  }, [visible])

  return (
    <div
      ref={ref}
      className={[
        'opacity-0 translate-y-7 transition duration-700 ease-rs',
        visible ? 'in !opacity-100 !translate-y-0' : null,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}
