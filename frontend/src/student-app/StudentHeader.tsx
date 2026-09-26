import { lazy, Suspense, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { SiteHeader, type SiteNavLink } from '../components/layout/SiteHeader'
import { Button } from '../components/ui/Button'
import { isStudentIdleProbePath, needsAuthBootstrap } from '../lib/auth-bootstrap'
import {
  getProfileDisplayNameOnce,
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

const STUDENT_NAV: SiteNavLink[] = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/courses', label: 'Courses' },
  { href: '/certificates', label: 'Certificates' },
  { href: '/research-team', label: 'Research Team' },
  { href: '/about', label: 'About Instructor' },
  { href: '/faq', label: 'FAQ' },
  { href: '/contact', label: 'Contact' },
]

function isOAuthCallback(search: string): boolean {
  const params = new URLSearchParams(search)
  const code = (params.get('code') ?? '').trim()
  const state = (params.get('state') ?? '').trim()
  return Boolean(code && state)
}

const FALLBACK_PROFILE_NAME = 'Student'

const signInLinkClass = 'rs-site-signin'

export function StudentHeader() {
  const [signedIn, setSignedIn] = useState(false)
  const [profileName, setProfileName] = useState(FALLBACK_PROFILE_NAME)
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
      }
      return
    }

    const ok = await probeSignedIn()
    if (!cancelled()) {
      setSignedIn(ok)
      if (ok) {
        void warmUserProfileOnce(true)
        const requestId = ++profileRequestRef.current
        void getProfileDisplayNameOnce().then((name) => {
          if (cancelled() || requestId !== profileRequestRef.current) return
          setProfileName(name?.trim() || FALLBACK_PROFILE_NAME)
        })
      } else {
        profileRequestRef.current += 1
        setProfileName(FALLBACK_PROFILE_NAME)
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

  const authOn = isAuthConfigured()

  let rightSlot: ReactNode = null
  let mobileCta: ReactNode = null

  if (authOn) {
    if (signedIn) {
      rightSlot = (
        <Suspense fallback={null}>
          <ProfileMenu
            name={profileName}
            subtitle="Student"
            items={[
              { href: '/account/profile', label: 'Account' },
              { label: 'Logout', onSelect: () => void handleSignOut() },
            ]}
          />
        </Suspense>
      )
      mobileCta = (
        <>
          <Button to="/dashboard" variant="primary">
            My Dashboard
          </Button>
          <Button to="/courses" variant="ghost">
            Explore Courses
          </Button>
        </>
      )
    } else {
      rightSlot = (
        <>
          <Link className={signInLinkClass} to="/login">
            Sign In
          </Link>
          <Button to="/register" size="sm" arrow>
            Create Account
          </Button>
        </>
      )
      mobileCta = (
        <>
          <Button to="/login" variant="ghost">
            Sign In
          </Button>
          <Button to="/register" variant="primary">
            Create Account
          </Button>
        </>
      )
    }
  }

  return (
    <SiteHeader
      links={STUDENT_NAV}
      activePath={location.pathname}
      homeHref="/"
      rightSlot={rightSlot}
      mobileCta={mobileCta}
    />
  )
}
