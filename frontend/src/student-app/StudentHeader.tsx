import { lazy, Suspense, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import logoMark from '../assets/prototype/Logo.jpg'
import { isStudentIdleProbePath, needsAuthBootstrap } from '../lib/auth-bootstrap'
import {
  getProfileHeaderIdentityOnce,
  lazySignOut,
  probeSignedIn,
  warmUserProfileOnce,
} from '../lib/auth-session-lazy'
import { clearClientAuthState } from '../lib/clear-client-auth-state'
import { isAuthConfigured } from '../lib/is-auth-configured'
import { isStudentSessionSuperseded } from '../lib/student-session-superseded-state'

const ProfileMenu = lazy(() =>
  import('../components/layout/ProfileMenu').then((m) => ({ default: m.ProfileMenu })),
)

const STUDENT_NAV = [
  { href: '/dashboard', label: 'Dashboard', route: 'dashboard' },
  { href: '/courses', label: 'Courses', route: 'courses' },
  { href: '/certificates', label: 'Certificates', route: 'certificates' },
  { href: '/research-team', label: 'Research Team', route: 'research-team' },
  { href: '/about', label: 'About Instructor', route: 'about' },
  { href: '/faq', label: 'FAQ', route: 'faq' },
  { href: '/contact', label: 'Contact', route: 'contact' },
] as const

function activeNavRoute(pathname: string): string {
  if (pathname === '/verify' || pathname.startsWith('/verify/')) return 'certificates'
  for (const link of STUDENT_NAV) {
    if (pathname === link.href || pathname.startsWith(`${link.href}/`)) return link.route
  }
  return ''
}

function ArrowIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ width: 17, height: 17, display: 'inline-block', verticalAlign: 'middle' }}
      aria-hidden="true"
    >
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

function isOAuthCallback(search: string): boolean {
  const params = new URLSearchParams(search)
  const code = (params.get('code') ?? '').trim()
  const state = (params.get('state') ?? '').trim()
  return Boolean(code && state)
}

const FALLBACK_PROFILE_NAME = 'Student'

export function StudentHeader() {
  const [signedIn, setSignedIn] = useState(false)
  const [profileName, setProfileName] = useState(FALLBACK_PROFILE_NAME)
  const [profileEmail, setProfileEmail] = useState<string | undefined>(undefined)
  const [profileGivenName, setProfileGivenName] = useState<string | undefined>(undefined)
  const [profileFamilyName, setProfileFamilyName] = useState<string | undefined>(undefined)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const burgerRef = useRef<HTMLButtonElement>(null)
  const mobileMenuRef = useRef<HTMLDivElement>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const hadOAuthCallbackRef = useRef(false)
  const profileRequestRef = useRef(0)

  const runSessionProbe = useCallback(async (cancelled: () => boolean) => {
    if (isStudentSessionSuperseded()) {
      if (!cancelled()) {
        profileRequestRef.current += 1
        setSignedIn(false)
        setProfileName(FALLBACK_PROFILE_NAME)
      }
      return
    }

    if (!isAuthConfigured()) {
      if (!cancelled()) {
        profileRequestRef.current += 1
        setSignedIn(false)
        setProfileName(FALLBACK_PROFILE_NAME)
        setProfileEmail(undefined)
        setProfileGivenName(undefined)
        setProfileFamilyName(undefined)
      }
      return
    }

    const ok = await probeSignedIn()
    if (!cancelled()) {
      setSignedIn(ok)
      if (ok) {
        void warmUserProfileOnce(true)
        const requestId = ++profileRequestRef.current
        void getProfileHeaderIdentityOnce().then((identity) => {
          if (cancelled() || requestId !== profileRequestRef.current) return
          if (!identity) {
            setProfileName(FALLBACK_PROFILE_NAME)
            setProfileEmail(undefined)
            setProfileGivenName(undefined)
            setProfileFamilyName(undefined)
            return
          }
          setProfileName(identity.name.trim() || FALLBACK_PROFILE_NAME)
          setProfileEmail(identity.email || undefined)
          setProfileGivenName(identity.givenName || undefined)
          setProfileFamilyName(identity.familyName || undefined)
        })
      } else {
        profileRequestRef.current += 1
        setProfileName(FALLBACK_PROFILE_NAME)
        setProfileEmail(undefined)
        setProfileGivenName(undefined)
        setProfileFamilyName(undefined)
      }
    }
  }, [])

  useEffect(() => {
    if (!isAuthConfigured()) return

    let cancelled = false
    let hubStop: (() => void) | undefined

    void import('aws-amplify/utils').then(({ Hub }) => {
      if (cancelled) return
      hubStop = Hub.listen('auth', ({ payload }) => {
        const event = payload.event as string
        if (event === 'signedIn') {
          void runSessionProbe(() => false)
        }
        if (event === 'signedOut') {
          profileRequestRef.current += 1
          setSignedIn(false)
          setProfileName(FALLBACK_PROFILE_NAME)
        }
      })
    })

    return () => {
      cancelled = true
      hubStop?.()
    }
  }, [runSessionProbe])

  useEffect(() => {
    let cancelled = false
    let idleId: number | undefined
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    const isCancelled = () => cancelled

    const scheduleProbe = (immediate = false) => {
      if (immediate) {
        void runSessionProbe(isCancelled)
        return
      }
      if (typeof requestIdleCallback === 'function') {
        idleId = requestIdleCallback(() => void runSessionProbe(isCancelled))
      } else {
        timeoutId = setTimeout(() => void runSessionProbe(isCancelled), 1)
      }
    }

    const { pathname: path, search } = location
    const oauthCallback = isOAuthCallback(search)

    if (oauthCallback) {
      hadOAuthCallbackRef.current = true
      return () => {
        cancelled = true
      }
    }

    const immediateAfterOAuth = hadOAuthCallbackRef.current && !oauthCallback
    if (immediateAfterOAuth) {
      hadOAuthCallbackRef.current = false
    }

    if (immediateAfterOAuth || needsAuthBootstrap(path, search)) {
      scheduleProbe(true)
    } else if (isStudentIdleProbePath(path)) {
      scheduleProbe(false)
    } else {
      scheduleProbe(true)
    }

    return () => {
      cancelled = true
      if (idleId != null && typeof cancelIdleCallback === 'function') {
        cancelIdleCallback(idleId)
      }
      if (timeoutId != null) clearTimeout(timeoutId)
    }
  }, [location, runSessionProbe])

  async function handleSignOut() {
    profileRequestRef.current += 1
    try {
      await lazySignOut()
    } catch {
      // Still clear local state even if Amplify signOut fails
    } finally {
      clearClientAuthState({ clearSupersededBanner: true })
      setSignedIn(false)
      setProfileName(FALLBACK_PROFILE_NAME)
      navigate('/', { replace: true })
    }
  }

  const closeMobileMenu = useCallback(() => {
    setMobileOpen(false)
    const menu = mobileMenuRef.current
    if (menu && document.activeElement instanceof Node && menu.contains(document.activeElement)) {
      burgerRef.current?.focus()
    }
  }, [])

  useEffect(() => {
    closeMobileMenu()
  }, [closeMobileMenu, location.pathname])

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
  }, [closeMobileMenu, mobileOpen])

  const authOn = isAuthConfigured()
  const activeRoute = activeNavRoute(location.pathname)

  let desktopCta: ReactNode = null
  let mobileCta: ReactNode = null

  if (authOn) {
    if (signedIn) {
      desktopCta = (
        <Suspense fallback={null}>
          <ProfileMenu
            chrome="prototype"
            name={profileName}
            email={profileEmail}
            givenName={profileGivenName}
            familyName={profileFamilyName}
            subtitle="Student"
            items={[
              { href: '/account/profile', label: 'Account' },
              { href: '/settings', label: 'Settings' },
              { label: 'Logout', onSelect: () => void handleSignOut() },
            ]}
          />
        </Suspense>
      )
      mobileCta = (
        <>
          <Link className="btn btn-primary" to="/dashboard" onClick={closeMobileMenu}>
            My Dashboard
            <ArrowIcon />
          </Link>
          <Link className="btn btn-ghost" to="/courses" onClick={closeMobileMenu}>
            Explore Courses
          </Link>
        </>
      )
    } else {
      desktopCta = (
        <>
          <Link className="login" to="/login">
            Sign In
          </Link>
          <Link className="btn btn-primary btn-sm" to="/register">
            Create Account
            <ArrowIcon />
          </Link>
        </>
      )
      mobileCta = (
        <>
          <Link className="btn btn-ghost" to="/login" onClick={closeMobileMenu}>
            Sign In
          </Link>
          <Link className="btn btn-primary" to="/register" onClick={closeMobileMenu}>
            Create Account
          </Link>
        </>
      )
    }
  }

  return (
    <>
      <header id="header" className={scrolled ? 'scrolled' : undefined}>
        <div className="wrap">
          <nav aria-label="Primary">
            <Link to="/" className="logo" aria-label="Research Spectrum home">
              <img className="mark" src={logoMark} alt="Research Spectrum" />
              <span className="word">
                <b>Research</b>
                <span>Spectrum</span>
              </span>
            </Link>
            <ul className="nav-links">
              {STUDENT_NAV.map((link) => {
                const active = link.route === activeRoute
                return (
                  <li key={link.href}>
                    <Link
                      to={link.href}
                      data-route={link.route}
                      className={active ? 'active' : undefined}
                      aria-current={active ? 'page' : undefined}
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      {link.label}
                    </Link>
                  </li>
                )
              })}
            </ul>
            <div className="nav-cta">
              {desktopCta}
              <button
                ref={burgerRef}
                type="button"
                className={mobileOpen ? 'burger open' : 'burger'}
                id="burger"
                aria-label="Open menu"
                aria-expanded={mobileOpen}
                aria-controls="mobileMenu"
                onClick={() => setMobileOpen((open) => !open)}
              >
                <span />
              </button>
            </div>
          </nav>
        </div>
      </header>
      <div
        ref={mobileMenuRef}
        className={mobileOpen ? 'mobile-menu open' : 'mobile-menu'}
        id="mobileMenu"
        aria-hidden={mobileOpen ? 'false' : 'true'}
      >
        <div className="links">
          {STUDENT_NAV.map((link) => {
            const active = link.route === activeRoute
            return (
              <Link
                key={link.href}
                to={link.href}
                data-route={link.route}
                className={active ? 'active' : undefined}
                aria-current={active ? 'page' : undefined}
                onClick={closeMobileMenu}
              >
                {link.label}
              </Link>
            )
          })}
        </div>
        {mobileCta ? <div className="mm-cta">{mobileCta}</div> : null}
      </div>
    </>
  )
}
