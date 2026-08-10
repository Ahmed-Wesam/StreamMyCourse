import { Link } from 'react-router-dom'

import { legalRouteLinks } from '../../lib/legal/links'

type FooterProps = {
  /** When set, legal links use absolute URLs on the student site (teacher shell). */
  legalBaseUrl?: string
}

export function Footer({ legalBaseUrl }: FooterProps) {
  return (
    <footer className="border-t border-slate-200/80 bg-gradient-to-r from-slate-50/95 via-white to-blue-50/35 backdrop-blur-[2px]">
      <div className="mx-auto max-w-7xl px-3 py-10 sm:px-5 lg:px-10">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <Link to="/" className="text-sm font-semibold text-gray-900">
            SPSS Spectrum
          </Link>
          <nav
            aria-label="Legal policies"
            className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-gray-600"
          >
            {legalRouteLinks.map(({ path, label }) =>
              legalBaseUrl ? (
                <a key={path} href={`${legalBaseUrl}${path}`} className="hover:text-gray-900">
                  {label}
                </a>
              ) : (
                <Link key={path} to={path} className="hover:text-gray-900">
                  {label}
                </Link>
              ),
            )}
          </nav>
        </div>
        <p className="mt-6 text-center text-xs text-gray-500">
          © {new Date().getFullYear()} SPSS Spectrum. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
