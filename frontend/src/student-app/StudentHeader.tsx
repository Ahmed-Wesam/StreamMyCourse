import { useAuthenticator } from '@aws-amplify/ui-react'
import { useEffect, useId, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { isAuthConfigured } from '../lib/auth'
import { useCognitoDisplayName } from '../lib/cognito-display-name'

export function StudentHeader() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const isHome = location.pathname === '/'
  const menuId = useId()

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

  const coursesHref = isHome ? '#courses' : '/#courses'
  const aboutHref = isHome ? '#about' : '/#about'
  const contactHref = isHome ? '#contact' : '/#contact'

  const { user, signOut, authStatus } = useAuthenticator((ctx) => [
    ctx.user,
    ctx.signOut,
    ctx.authStatus,
  ])
  const signedIn = isAuthConfigured() && authStatus === 'authenticated'
  const { label: displayName, title: displayNameTitle, ready: displayNameReady } =
    useCognitoDisplayName(user?.username)

  const linkClass =
    'block rounded-md px-3 py-2.5 text-base font-medium text-gray-800 hover:bg-gray-50 active:bg-gray-100'

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-30 border-b border-slate-200/90 bg-white/95 backdrop-blur-sm transition-shadow ${
        scrolled ? 'shadow-sm shadow-slate-300/25' : ''
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-3 sm:px-5 lg:px-10">
        <Link to="/" className="flex min-w-0 items-center gap-2">
          <span className="truncate text-xl font-bold tracking-tight text-gray-900">StreamMyCourse</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Main">
          <a
            href={coursesHref}
            className="text-sm font-medium text-gray-700 transition-colors hover:text-gray-900"
          >
            Courses
          </a>
          <a
            href={aboutHref}
            className="text-sm font-medium text-gray-700 transition-colors hover:text-gray-900"
          >
            About
          </a>
          <a
            href={contactHref}
            className="text-sm font-medium text-gray-700 transition-colors hover:text-gray-900"
          >
            Contact
          </a>
          {isAuthConfigured() &&
            (signedIn ? (
              <>
                {displayNameReady ? (
                  <span
                    className="max-w-[10rem] truncate text-sm font-medium text-gray-700 transition-colors hover:text-gray-900"
                    title={displayNameTitle}
                  >
                    {displayName}
                  </span>
                ) : null}
                <button
                  type="button"
                  className="text-sm font-medium text-emerald-700 hover:text-emerald-800"
                  onClick={() => void signOut()}
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link to="/login" className="text-sm font-medium text-emerald-700 hover:text-emerald-800">
                Sign in
              </Link>
            ))}
        </nav>

        <div className="flex items-center md:hidden">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md p-2 text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            aria-expanded={mobileOpen}
            aria-controls={menuId}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMobileOpen((o) => !o)}
          >
            {mobileOpen ? (
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-30 bg-black/25 md:hidden"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <nav
            id={menuId}
            className="absolute left-0 right-0 top-full z-40 border-b border-gray-200 bg-white shadow-lg md:hidden"
            aria-label="Mobile"
          >
            <div className="mx-auto max-w-7xl space-y-0.5 px-3 py-3 sm:px-5 lg:px-10">
              <a href={coursesHref} className={linkClass} onClick={() => setMobileOpen(false)}>
                Courses
              </a>
              <a href={aboutHref} className={linkClass} onClick={() => setMobileOpen(false)}>
                About
              </a>
              <a href={contactHref} className={linkClass} onClick={() => setMobileOpen(false)}>
                Contact
              </a>
              {isAuthConfigured() &&
                (signedIn ? (
                  <>
                    {displayNameReady ? (
                      <span className={linkClass} title={displayNameTitle}>
                        {displayName}
                      </span>
                    ) : null}
                    <button
                      type="button"
                      className={`${linkClass} w-full text-left text-emerald-700`}
                      onClick={() => {
                        setMobileOpen(false)
                        void signOut()
                      }}
                    >
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link to="/login" className={`${linkClass} text-emerald-700`} onClick={() => setMobileOpen(false)}>
                    Sign in
                  </Link>
                ))}
            </div>
          </nav>
        </>
      )}
    </header>
  )
}
