import type { ReactNode } from 'react'
import { Footer } from './Footer'

type LayoutProps = {
  children: ReactNode
  /** When false, only renders children (e.g. full-bleed player). */
  showChrome?: boolean
  /** Fixed app chrome (e.g. `StudentHeader` / `TeacherHeader`). Shells clear the bar themselves; main does not add `pt-16`. */
  chromeHeader?: ReactNode
}

export function Layout({ children, showChrome = true, chromeHeader }: LayoutProps) {
  if (!showChrome) {
    return <>{children}</>
  }

  /** Full-bleed width; no bottom padding so full-bleed sections (e.g. CTA band) meet the footer flush. */
  const mainInnerClass = chromeHeader ? 'w-full' : 'w-full pt-5'

  return (
    <div className="flex min-h-screen flex-col bg-transparent">
      {chromeHeader}
      <main className="min-w-0 flex-1">
        <div className={mainInnerClass}>{children}</div>
      </main>
      <Footer />
    </div>
  )
}
