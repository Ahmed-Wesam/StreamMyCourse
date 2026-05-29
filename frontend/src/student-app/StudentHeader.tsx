import { useCallback, useEffect, useId, useRef, useState } from 'react'

import { Link, useLocation, useNavigate } from 'react-router-dom'

import { BarChart2, Menu } from 'lucide-react'

import { Hub } from 'aws-amplify/utils'

import { needsAuthBootstrap } from '../lib/auth-bootstrap'

import { lazySignOut, probeSignedIn, warmUserProfileOnce } from '../lib/auth-session-lazy'

import { clearClientAuthState } from '../lib/clear-client-auth-state'
import { clearSessionSupersededBanner } from '../lib/session-superseded-banner'

import { isAuthConfigured } from '../lib/auth'



const COURSE_DETAIL = /^\/courses\/[^/]+$/



function isPublicRoute(pathname: string): boolean {

  return (

    pathname === '/' ||

    pathname === '/details' ||

    pathname === '/learn' ||

    pathname === '/courses' ||

    COURSE_DETAIL.test(pathname)

  )

}



function isOAuthCallback(search: string): boolean {

  const params = new URLSearchParams(search)

  const code = (params.get('code') ?? '').trim()

  const state = (params.get('state') ?? '').trim()

  return Boolean(code && state)

}



export function StudentHeader() {

  const [scrolled, setScrolled] = useState(false)

  const [mobileOpen, setMobileOpen] = useState(false)

  const [signedIn, setSignedIn] = useState(false)

  const location = useLocation()

  const navigate = useNavigate()

  const menuId = useId()

  const hadOAuthCallbackRef = useRef(false)



  const pathname = location.pathname

  const hash = location.hash

  const isActive = (to: string) => pathname === to

  const isCoursesList = pathname === '/courses'

  const isAccount = pathname.startsWith('/account')

  const isCoursePricing = pathname === '/details' && hash === '#pricing'

  const navItemClass = (active: boolean) =>

    [

      'px-4 py-2 rounded-xl text-sm transition-colors',

      active

        ? 'bg-blue-50 text-blue-700 font-semibold'

        : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground font-medium',

    ].join(' ')



  const runSessionProbe = useCallback(async (cancelled: () => boolean) => {

    if (!isAuthConfigured()) {

      if (!cancelled()) setSignedIn(false)

      return

    }

    const ok = await probeSignedIn()

    if (!cancelled()) {

      setSignedIn(ok)

      if (ok) void warmUserProfileOnce(true)

    }

  }, [])



  useEffect(() => {

    const onScroll = () => setScrolled(window.scrollY > 4)

    onScroll()

    window.addEventListener('scroll', onScroll, { passive: true })

    return () => window.removeEventListener('scroll', onScroll)

  }, [])



  useEffect(() => {

    setMobileOpen(false)

  }, [location.pathname, location.search])



  useEffect(() => {

    if (!mobileOpen) return

    const onKey = (e: KeyboardEvent) => {

      if (e.key === 'Escape') setMobileOpen(false)

    }

    window.addEventListener('keydown', onKey)

    return () => window.removeEventListener('keydown', onKey)

  }, [mobileOpen])



  useEffect(() => {

    if (!isAuthConfigured()) return

    const hubStop = Hub.listen('auth', ({ payload }) => {

      const event = payload.event as string

      if (event === 'signedIn') {

        void runSessionProbe(() => false)

      }

      if (event === 'signedOut') {

        setSignedIn(false)

      }

    })

    return () => hubStop()

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



    const immediateAfterOAuth =

      hadOAuthCallbackRef.current && !oauthCallback

    if (immediateAfterOAuth) {

      hadOAuthCallbackRef.current = false

    }



    if (immediateAfterOAuth || needsAuthBootstrap(path, search)) {

      scheduleProbe(true)

    } else if (isPublicRoute(path)) {

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

  }, [location.pathname, location.search, location.hash, runSessionProbe])



  async function handleSignOut() {

    try {

      await lazySignOut()

    } catch {

      // Still clear local state even if Amplify signOut fails

    } finally {

      clearClientAuthState()

      clearSessionSupersededBanner()

      setSignedIn(false)

      setMobileOpen(false)

      navigate('/', { replace: true })

    }

  }



  return (

    <header className={`sticky top-0 z-50 border-b border-border bg-white transition-shadow ${scrolled ? 'shadow-sm' : ''}`}>

      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">

        <Link className="flex items-center gap-2 text-primary" to="/">

          <BarChart2 className="w-6 h-6" />

          <span className="font-bold text-[1.1rem]">SPSS Spectrum</span>

        </Link>



        <nav className="hidden md:flex items-center gap-1" aria-label="Primary">

          <Link className={navItemClass(isActive('/'))} to="/">

            Home

          </Link>

          <Link className={navItemClass(isActive('/details') && !isCoursePricing)} to="/details">

            Details

          </Link>

          <a className={navItemClass(isCoursePricing)} href="/details#pricing">

            Pricing

          </a>

          <Link className={navItemClass(isCoursesList)} to="/courses">

            Courses

          </Link>

        </nav>



        <div className="hidden md:flex items-center gap-3">

          {isAuthConfigured() ? (

            <>

              <Link className={navItemClass(isAccount)} to="/account/profile">

                Account

              </Link>

              {signedIn ? (

                <button

                  type="button"

                  className="px-4 py-2 rounded-md text-sm font-semibold text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"

                  onClick={() => void handleSignOut()}

                >

                  Sign out

                </button>

              ) : (

                <Link

                  className="px-4 py-2 rounded-md text-sm font-semibold text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"

                  to="/login"

                >

                  Sign in

                </Link>

              )}

            </>

          ) : null}

          <a className="bg-primary text-white px-5 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors font-semibold" href="/details#pricing">

            Enroll Now

          </a>

        </div>



        <button

          type="button"

          className="md:hidden p-2 rounded-md text-muted-foreground hover:text-foreground"

          aria-expanded={mobileOpen}

          aria-controls={menuId}

          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}

          onClick={() => setMobileOpen((o) => !o)}

        >

          <Menu className="w-5 h-5" />

        </button>

      </div>



      {mobileOpen && (

        <nav id={menuId} className="md:hidden border-t border-border bg-white" aria-label="Primary mobile">

          <div className="px-6 py-3 flex flex-col gap-2">

            <Link to="/" onClick={() => setMobileOpen(false)} className={navItemClass(isActive('/'))}>

              Home

            </Link>

            <Link

              to="/details"

              onClick={() => setMobileOpen(false)}

              className={navItemClass(isActive('/details') && !isCoursePricing)}

            >

              Details

            </Link>

            <a

              href="/details#pricing"

              onClick={() => setMobileOpen(false)}

              className={navItemClass(isCoursePricing)}

            >

              Pricing

            </a>

            <Link to="/courses" onClick={() => setMobileOpen(false)} className={navItemClass(isCoursesList)}>

              Courses

            </Link>

            {isAuthConfigured() ? (

              <>

                <Link

                  to="/account/profile"

                  onClick={() => setMobileOpen(false)}

                  className={navItemClass(isAccount)}

                >

                  Account

                </Link>

                {signedIn ? (

                  <button

                    type="button"

                    onClick={() => void handleSignOut()}

                    className="px-3 py-2 rounded-xl hover:bg-muted/50 text-left text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"

                  >

                    Sign out

                  </button>

                ) : (

                  <Link

                    to="/login"

                    onClick={() => setMobileOpen(false)}

                    className="px-3 py-2 rounded-xl hover:bg-muted/50 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"

                  >

                    Sign in

                  </Link>

                )}

              </>

            ) : null}

            <a href="/details#pricing" className="mt-2 bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold text-center">

              Enroll Now

            </a>

          </div>

        </nav>

      )}

    </header>

  )

}


