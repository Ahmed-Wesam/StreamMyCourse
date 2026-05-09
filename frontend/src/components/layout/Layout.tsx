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

  /** Keep content full-bleed; pages own their inner max-width. */
  const mainInnerClass = chromeHeader ? 'w-full pb-12' : 'w-full pb-12 pt-5'

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
