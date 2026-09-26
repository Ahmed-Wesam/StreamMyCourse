import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { Link } from 'react-router-dom'

import brandMark from '../../assets/brand/research-spectrum-mark.webp'

export type SiteNavLink = { href: string; label: string }

type SiteHeaderProps = {
  links: SiteNavLink[]
  /** Current pathname used for aria-current and to close the mobile menu when it changes. */
  activePath: string
  homeHref?: string
  /** Optional node next to the wordmark (teacher "Instructor" badge). */
  badge?: ReactNode
  /**
   * Desktop right cluster (sign-in buttons or profile).
   * Hidden below the nav breakpoint the same way as desktop links — SiteHeader wraps it in `hidden nav:flex`.
   */
  rightSlot?: ReactNode
  /** Rendered at the bottom of the open mobile menu. */
  mobileCta?: ReactNode
}

function isActivePath(activePath: string, href: string): boolean {
  if (activePath === href) return true
  if (href === '/') return false
  return activePath.startsWith(`${href}/`) || activePath.startsWith(href)
}

function isExternalHref(href: string): boolean {
  return /^https?:\/\//i.test(href)
}

function NavAnchor({
  href,
  children,
  className,
  active,
  onClick,
}: {
  href: string
  children: ReactNode
  className: string
  active: boolean
  onClick?: () => void
}) {
  const ariaCurrent = active ? ('page' as const) : undefined

  if (isExternalHref(href)) {
    return (
      <a href={href} className={className} aria-current={ariaCurrent} onClick={onClick}>
        {children}
      </a>
    )
  }

  return (
    <Link to={href} className={className} aria-current={ariaCurrent} onClick={onClick}>
      {children}
    </Link>
  )
}

function cx(...parts: Array<string | undefined | false>) {
  return parts.filter(Boolean).join(' ')
}

function BrandLockup({ homeHref }: { homeHref: string }) {
  const content = (
    <>
      <img
        src={brandMark}
        alt="Research Spectrum"
        className="rs-site-mark"
      />
      <span
        aria-hidden="true"
        className="rs-site-word"
      >
        <span className="text-rs-navy-800">Research</span>
        <span className="text-rs-blue">Spectrum</span>
      </span>
    </>
  )
  const className = 'rs-site-lockup'
  if (isExternalHref(homeHref)) {
    return (
      <a href={homeHref} className={className}>
        {content}
      </a>
    )
  }
  return (
    <Link to={homeHref} className={className}>
      {content}
    </Link>
  )
}

export function SiteHeader({
  links,
  activePath,
  homeHref = '/',
  badge,
  rightSlot,
  mobileCta,
}: SiteHeaderProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const mobileMenuId = useId()
  const burgerRef = useRef<HTMLButtonElement>(null)
  const mobileNavRef = useRef<HTMLElement>(null)

  function closeMobileMenu() {
    setMobileOpen(false)
    const nav = mobileNavRef.current
    if (nav && document.activeElement instanceof Node && nav.contains(document.activeElement)) {
      burgerRef.current?.focus()
    }
  }

  useEffect(() => {
    closeMobileMenu()
  }, [activePath])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!mobileOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMobileMenu()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [mobileOpen])

  return (
    <header className={cx('rs-site-header', scrolled && 'rs-site-header-scrolled')}>
      <div className="rs-site-bar">
        <div className="rs-site-brand">
          <BrandLockup homeHref={homeHref} />
          {badge}
        </div>

        <nav aria-label="Primary" className="rs-site-desktop-nav">
          {links.map((link) => {
            const active = isActivePath(activePath, link.href)
            return (
              <NavAnchor
                key={`d:${link.href}:${link.label}`}
                href={link.href}
                active={active}
                className={cx('rs-site-nav-link', active && 'rs-site-nav-link-active')}
              >
                {link.label}
              </NavAnchor>
            )
          })}
        </nav>

        <div className="rs-site-tools">
          {rightSlot ? <div className="rs-site-desktop-slot">{rightSlot}</div> : null}

          <button
            type="button"
            className={cx('rs-site-menu-btn', mobileOpen && 'bg-rs-sky-2')}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
            ref={burgerRef}
            aria-controls={mobileMenuId}
            onClick={() => setMobileOpen((v) => !v)}
          >
            <span
              aria-hidden="true"
              className={cx('rs-site-burger', mobileOpen && 'rs-site-burger-open')}
            />
          </button>
        </div>
      </div>

      <nav
        ref={mobileNavRef}
        id={mobileMenuId}
        aria-label="Primary mobile"
        aria-hidden={mobileOpen ? 'false' : 'true'}
        className={cx('rs-site-mobile-nav', mobileOpen ? 'block' : 'hidden')}
      >
        {links.map((link) => {
          const active = isActivePath(activePath, link.href)
          return (
            <NavAnchor
              key={`m:${link.href}:${link.label}`}
              href={link.href}
              active={active}
              className={cx('rs-site-mobile-link', active && 'text-rs-blue')}
              onClick={closeMobileMenu}
            >
              {link.label}
            </NavAnchor>
          )
        })}
        {mobileCta ? <div className="mt-4 flex flex-col gap-2.5">{mobileCta}</div> : null}
      </nav>
    </header>
  )
}
