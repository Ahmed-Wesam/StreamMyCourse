import type { ReactNode } from 'react'
import { Footer } from './Footer'

type LayoutProps = {
  children: ReactNode
  /** When false, only renders children (e.g. full-bleed player). */
  showChrome?: boolean
  /**
   * Fixed app chrome (e.g. `StudentHeader` / `TeacherHeader`). When set, main content gets top
   * padding to clear the `h-16` bar — shells should not duplicate `pt-16`.
   */
  chromeHeader?: ReactNode
}

export function Layout({ children, showChrome = true, chromeHeader }: LayoutProps) {
  if (!showChrome) {
    return <>{children}</>
  }

  /** `pt-20` clears the fixed `h-16` bar plus ~1rem air gap so page chrome (e.g. hero) does not sit flush under the header. */
  const mainInnerClass = chromeHeader
    ? 'mx-auto w-full max-w-7xl px-3 pb-12 pt-20 sm:px-5 sm:pb-14 sm:pt-20 lg:px-10'
    : 'mx-auto w-full max-w-7xl px-3 pb-12 pt-5 sm:px-5 sm:pb-14 sm:pt-7 lg:px-10'

  return (
    <div className="relative flex min-h-screen flex-col bg-gradient-to-b from-slate-300/35 via-slate-100 to-indigo-100/25">
      {/* Soft vignette + dot texture — keeps gutters from feeling flat */}
      <div
        className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_90%_55%_at_50%_-15%,rgba(99,102,241,0.07),transparent_65%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none fixed inset-0 bg-dot-grid bg-[length:26px_26px] opacity-[0.55]"
        aria-hidden
      />
      <div className="relative z-0 flex min-h-screen flex-col">
        {chromeHeader}
        <main className="min-w-0 flex-1">
          <div className={mainInnerClass}>{children}</div>
        </main>
        <Footer />
      </div>
    </div>
  )
}
