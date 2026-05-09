import { useEffect, useId, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { BarChart2, Menu } from 'lucide-react'
import { signOut } from 'aws-amplify/auth'
import { hasSignedInIdToken } from '../lib/api'
import { isAuthConfigured } from '../lib/auth'

function clearClientAuthState() {
  try {
    localStorage.clear()
  } catch {
    /* ignore */
  }
  try {
    sessionStorage.clear()
  } catch {
    /* ignore */
  }

  // Best-effort cookie clearing (won't remove HttpOnly cookies).
  try {
    const cookies = document.cookie ? document.cookie.split(';') : []
    for (const raw of cookies) {
      const eqPos = raw.indexOf('=')
      const name = (eqPos > -1 ? raw.slice(0, eqPos) : raw).trim()
      if (!name) continue
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
    }
  } catch {
    /* ignore */
  }
}

export function StudentHeader() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const menuId = useId()

  const pathname = location.pathname
  const hash = location.hash
  const isActive = (to: string) => pathname === to
  const isCoursePricing = pathname === '/course' && hash === '#pricing'
  const navItemClass = (active: boolean) =>
    [
      'px-4 py-2 rounded-xl text-sm transition-colors',
      active
        ? 'bg-blue-50 text-blue-700 font-semibold'
        : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground font-medium',
    ].join(' ')

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
    let cancelled = false
    async function run() {
      if (!isAuthConfigured()) {
        if (!cancelled) setSignedIn(false)
        return
      }
      const ok = await hasSignedInIdToken()
      if (!cancelled) setSignedIn(ok)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSignOut() {
    try {
      await signOut()
    } catch {
      // Still clear local state even if Amplify signOut fails
    } finally {
      clearClientAuthState()
      setSignedIn(false)
      setMobileOpen(false)
      navigate('/', { replace: true })
    }
  }

  return (
    <header className={`sticky top-0 z-50 bg-white border-b border-border transition-shadow ${scrolled ? 'shadow-sm' : ''}`}>
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link className="flex items-center gap-2 text-primary" to="/">
          <BarChart2 className="w-6 h-6" />
          <span className="font-bold text-[1.1rem]">SPSS Spectrum</span>
        </Link>

        <nav className="hidden md:flex items-center gap-1" aria-label="Primary">
          <Link className={navItemClass(isActive('/'))} to="/">
            Home
          </Link>
          <Link className={navItemClass(isActive('/course') && !isCoursePricing)} to="/course">
            Course
          </Link>
          <a className={navItemClass(isCoursePricing)} href="/course#pricing">
            Pricing
          </a>
          <Link className={navItemClass(isActive('/my-course'))} to="/my-course">
            My Course
          </Link>
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {isAuthConfigured() ? (
            signedIn ? (
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
            )
          ) : null}
          <a className="bg-primary text-white px-5 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors font-semibold" href="/course#pricing">
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
              to="/course"
              onClick={() => setMobileOpen(false)}
              className={navItemClass(isActive('/course') && !isCoursePricing)}
            >
              Course
            </Link>
            <a
              href="/course#pricing"
              onClick={() => setMobileOpen(false)}
              className={navItemClass(isCoursePricing)}
            >
              Pricing
            </a>
            <Link to="/my-course" onClick={() => setMobileOpen(false)} className={navItemClass(isActive('/my-course'))}>
              My Course
            </Link>
            {isAuthConfigured() ? (
              signedIn ? (
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
              )
            ) : null}
            <a href="/course#pricing" className="mt-2 bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold text-center">
              Enroll Now
            </a>
          </div>
        </nav>
      )}
    </header>
  )
}
