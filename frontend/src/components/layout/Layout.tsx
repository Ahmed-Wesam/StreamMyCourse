import type { ReactNode } from 'react'
import { Footer } from './Footer'

type LayoutProps = {
  children: ReactNode
  /** When false, only renders children (e.g. full-bleed player). */
  showChrome?: boolean
  /** Fixed app chrome (e.g. `StudentHeader` / `TeacherHeader`). Shells clear the bar themselves; main does not add `pt-16`. */
  chromeHeader?: ReactNode
  /** Full-width alert strip rendered directly under the header (e.g. session superseded). */
  chromeAlert?: ReactNode
  /** Student site origin for absolute legal footer links (teacher shell). */
  legalBaseUrl?: string
}

export function Layout({ children, showChrome = true, chromeHeader, chromeAlert, legalBaseUrl }: LayoutProps) {
  if (!showChrome) {
    return <>{children}</>
  }

  /** Full-bleed width; no bottom padding so full-bleed sections (e.g. CTA band) meet the footer flush. */
  const mainInnerClass = chromeHeader ? 'w-full' : 'w-full pt-5'

  return (
    <div className="flex min-h-screen flex-col bg-transparent">
      {chromeHeader}
      {chromeAlert}
      <main className="min-w-0 flex-1">
        <div className={mainInnerClass}>{children}</div>
      </main>
      <Footer legalBaseUrl={legalBaseUrl} />
    </div>
  )
}
