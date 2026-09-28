const COURSE_DETAIL = /^\/courses\/[^/]+$/
const LESSON_PLAYER = /^\/courses\/[^/]+\/lessons\//
const MODULE_QUIZ = /^\/courses\/[^/]+\/modules\/[^/]+\/quiz/

const AUTH_SELF_SERVICE =
  /^\/(login|register|verify-email|forgot-password|reset-password)(\/|$)/

/**
 * Public student paths that idle-probe auth after paint (do not import auth immediately).
 * Keep in sync with marketing + catalog surfaces that should stay first-paint light.
 */
export function isStudentIdleProbePath(pathname: string): boolean {
  return (
    pathname === '/' ||
    pathname === '/details' ||
    pathname === '/learn' ||
    pathname === '/courses' ||
    pathname === '/about' ||
    pathname === '/faq' ||
    pathname === '/contact' ||
    pathname === '/research-team' ||
    pathname === '/terms' ||
    pathname === '/privacy' ||
    pathname === '/refund' ||
    pathname === '/delivery' ||
    pathname === '/educational-disclaimer' ||
    COURSE_DETAIL.test(pathname)
  )
}

const TERMS_GATE_LEGAL_PATHS = new Set([
  '/terms',
  '/privacy',
  '/refund',
  '/delivery',
  '/educational-disclaimer',
])

/** Routes where missing terms acceptance must not force redirect to account. */
export function isStudentTermsGateExemptPath(pathname: string): boolean {
  if (pathname === '/') return true
  if (pathname.startsWith('/account')) return true
  if (AUTH_SELF_SERVICE.test(pathname)) return true
  if (TERMS_GATE_LEGAL_PATHS.has(pathname)) return true
  return false
}

/**
 * Whether the current route should run auth bootstrap (session restore / OAuth callback).
 */
export function needsAuthBootstrap(pathname: string, search: string): boolean {
  const params = new URLSearchParams(search)
  const code = (params.get('code') ?? '').trim()
  const state = (params.get('state') ?? '').trim()
  if (code && state) {
    return true
  }

  // Same set as isStudentIdleProbePath — public marketing/catalog/legal stay off AuthShell.
  if (isStudentIdleProbePath(pathname)) {
    return false
  }

  if (
    AUTH_SELF_SERVICE.test(pathname) ||
    pathname.startsWith('/account') ||
    pathname.startsWith('/billing') ||
    pathname.startsWith('/checkout') ||
    LESSON_PLAYER.test(pathname) ||
    MODULE_QUIZ.test(pathname)
  ) {
    return true
  }

  return false
}
