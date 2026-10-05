import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import brandMark from '../../assets/brand/research-spectrum-mark.webp'
import logoMark from '../../assets/prototype/Logo.jpg'
import { BRAND_NAME, BRAND_TAGLINE, FOOTER_BLURB } from '../../lib/brand'
import { legalRouteLinks } from '../../lib/legal/links'

type FooterProps = {
  /** When set, legal links use absolute URLs on the student site (teacher shell). */
  legalBaseUrl?: string
  /** Student shell uses prototype footer markup. Teacher keeps the default. */
  variant?: 'prototype'
}

const PLATFORM_LINKS = [
  { path: '/courses', label: 'Courses' },
  { path: '/certificates', label: 'Certificates' },
  { path: '/about', label: 'About Instructor' },
  { path: '/faq', label: 'FAQ' },
  { path: '/contact', label: 'Contact' },
] as const

const ACCOUNT_LINKS = [
  { path: '/login', label: 'Sign In' },
  { path: '/register', label: 'Create Account' },
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/account/profile', label: 'My Account' },
] as const

function FooterNavLink({
  path,
  legalBaseUrl,
  children,
}: {
  path: string
  legalBaseUrl?: string
  children: ReactNode
}) {
  const className = 'text-[14.5px] text-rs-body transition-colors duration-200 hover:text-rs-blue'

  if (legalBaseUrl) {
    return (
      <a href={`${legalBaseUrl}${path}`} className={className}>
        {children}
      </a>
    )
  }

  return (
    <Link to={path} className={className}>
      {children}
    </Link>
  )
}

function BrandLockup({ homeHref, external }: { homeHref: string; external: boolean }) {
  const className = 'flex items-center gap-[11px] no-underline'
  const content = (
    <>
      <img
        src={brandMark}
        alt="Research Spectrum"
        className="h-[38px] w-auto shrink-0 object-contain"
      />
      <span
        aria-hidden="true"
        className="text-xl font-extrabold leading-none tracking-[-0.02em]"
      >
        <span className="text-rs-navy-800">Research</span>
        <span className="text-rs-blue">Spectrum</span>
      </span>
    </>
  )

  if (external) {
    return (
      <a href={homeHref} className={className} aria-label="Research Spectrum">
        {content}
      </a>
    )
  }

  return (
    <Link to={homeHref} className={className} aria-label="Research Spectrum">
      {content}
    </Link>
  )
}

function LinkColumn({
  title,
  links,
  legalBaseUrl,
}: {
  title: string
  links: ReadonlyArray<{ path: string; label: string }>
  legalBaseUrl?: string
}) {
  return (
    <div>
      <h4 className="mb-4 text-[13px] font-bold uppercase tracking-[0.08em] text-rs-muted">
        {title}
      </h4>
      <ul className="list-none">
        {links.map(({ path, label }) => (
          <li key={path} className="mb-[11px]">
            <FooterNavLink path={path} legalBaseUrl={legalBaseUrl}>
              {label}
            </FooterNavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PrototypeFooter() {
  const year = new Date().getFullYear()
  const columns = [
    { title: 'Platform', links: PLATFORM_LINKS },
    { title: 'Legal', links: legalRouteLinks },
    { title: 'Account', links: ACCOUNT_LINKS },
  ] as const

  return (
    <footer>
      <div className="wrap">
        <div className="foot-grid">
          <div>
            <Link to="/" className="logo" aria-label="Research Spectrum">
              <img className="mark" src={logoMark} alt="Research Spectrum" />
              <span className="word">
                <b>Research</b>
                <span>Spectrum</span>
              </span>
            </Link>
            <p>{FOOTER_BLURB}</p>
          </div>
          {columns.map((column) => (
            <div key={column.title}>
              <h4>{column.title}</h4>
              <ul>
                {column.links.map(({ path, label }) => (
                  <li key={path}>
                    <Link to={path}>{label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="foot-bottom">
          <span>
            © {year} {BRAND_NAME}. {BRAND_TAGLINE}.
          </span>
          <div className="foot-social">
            <a
              href="https://instagram.com/researchspectrum"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Instagram"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="2" y="2" width="20" height="20" rx="5" />
                <circle cx="12" cy="12" r="4" />
                <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
              </svg>
            </a>
            <a href="#" aria-label="LinkedIn">
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 4.98 2.12 4.98 3.5zM.5 8h4V23h-4V8zm7 0h3.8v2.05h.05c.53-1 1.84-2.05 3.78-2.05 4.04 0 4.79 2.66 4.79 6.12V23h-4v-6.6c0-1.57-.03-3.6-2.19-3.6-2.19 0-2.53 1.71-2.53 3.48V23h-4V8z" />
              </svg>
            </a>
            <a href="#" aria-label="YouTube">
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M23 7.5a3 3 0 0 0-2.1-2.1C19 5 12 5 12 5s-7 0-8.9.4A3 3 0 0 0 1 7.5 31 31 0 0 0 .6 12 31 31 0 0 0 1 16.5a3 3 0 0 0 2.1 2.1C5 19 12 19 12 19s7 0 8.9-.4a3 3 0 0 0 2.1-2.1A31 31 0 0 0 23.4 12 31 31 0 0 0 23 7.5zM9.8 15.3V8.7l5.7 3.3z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}

export function Footer({ legalBaseUrl, variant }: FooterProps) {
  if (variant === 'prototype') return <PrototypeFooter />

  const homeHref = legalBaseUrl ? legalBaseUrl : '/'
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-rs-line bg-white pb-8 pt-16">
      <div className="mx-auto max-w-wrap px-7">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 sm:gap-8 lg:grid-cols-[1.6fr_1fr_1fr_1fr] lg:gap-10">
          <div>
            <BrandLockup homeHref={homeHref} external={Boolean(legalBaseUrl)} />
            <p className="mt-[18px] max-w-[320px] text-[14.5px] leading-relaxed text-rs-body">
              {FOOTER_BLURB}
            </p>
          </div>
          <LinkColumn title="Platform" links={PLATFORM_LINKS} legalBaseUrl={legalBaseUrl} />
          <LinkColumn title="Legal" links={legalRouteLinks} legalBaseUrl={legalBaseUrl} />
          <LinkColumn title="Account" links={ACCOUNT_LINKS} legalBaseUrl={legalBaseUrl} />
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-rs-line pt-[26px] text-[13.5px] text-rs-muted">
          <span>
            © {year} {BRAND_NAME}. {BRAND_TAGLINE}
          </span>
          <div className="flex gap-2.5">
            <a
              href="https://instagram.com/researchspectrum"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Instagram"
              className="rs-foot-social"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-5 w-5"
                aria-hidden="true"
              >
                <rect x="2" y="2" width="20" height="20" rx="5" />
                <circle cx="12" cy="12" r="4" />
                <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
              </svg>
            </a>
            <a
              href="#"
              aria-label="LinkedIn"
              className="rs-foot-social"
            >
              <svg
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-5 w-5"
                aria-hidden="true"
              >
                <path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 4.98 2.12 4.98 3.5zM.5 8h4V23h-4V8zm7 0h3.8v2.05h.05c.53-1 1.84-2.05 3.78-2.05 4.04 0 4.79 2.66 4.79 6.12V23h-4v-6.6c0-1.57-.03-3.6-2.19-3.6-2.19 0-2.53 1.71-2.53 3.48V23h-4V8z" />
              </svg>
            </a>
            <a
              href="#"
              aria-label="YouTube"
              className="rs-foot-social"
            >
              <svg
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-5 w-5"
                aria-hidden="true"
              >
                <path d="M23 7.5a3 3 0 0 0-2.1-2.1C19 5 12 5 12 5s-7 0-8.9.4A3 3 0 0 0 1 7.5 31 31 0 0 0 .6 12 31 31 0 0 0 1 16.5a3 3 0 0 0 2.1 2.1C5 19 12 19 12 19s7 0 8.9-.4a3 3 0 0 0 2.1-2.1A31 31 0 0 0 23.4 12 31 31 0 0 0 23 7.5zM9.8 15.3V8.7l5.7 3.3z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
