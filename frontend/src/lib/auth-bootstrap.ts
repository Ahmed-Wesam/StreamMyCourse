const COURSE_DETAIL = /^\/courses\/[^/]+$/
const LESSON_PLAYER = /^\/courses\/[^/]+\/lessons\//
const MODULE_QUIZ = /^\/courses\/[^/]+\/modules\/[^/]+\/quiz/

const AUTH_SELF_SERVICE =
  /^\/(login|register|verify-email|forgot-password|reset-password)(\/|$)/

/**
 * Public student paths that idle-probe auth after paint (do not import auth immediately).
 * Keep in sync with marketing + catalog surfaces that should stay first-paint light.
 */
const CERTIFICATE_VERIFY = /^\/verify(\/|$)/

function normalizeStudentPath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1)
  }
  return pathname
}

export function isStudentIdleProbePath(pathname: string): boolean {
  const path = normalizeStudentPath(pathname)
  return (
    path === '/' ||
    path === '/details' ||
    path === '/learn' ||
    path === '/courses' ||
    path === '/about' ||
    path === '/faq' ||
    path === '/contact' ||
    path === '/research-team' ||
    path === '/terms' ||
    path === '/privacy' ||
    path === '/refund' ||
    path === '/delivery' ||
    path === '/educational-disclaimer' ||
    CERTIFICATE_VERIFY.test(path) ||
    COURSE_DETAIL.test(path)
  )
}

/** Routes where missing terms acceptance must not force redirect to account. */
export function isStudentTermsGateExemptPath(pathname: string): boolean {
  const path = normalizeStudentPath(pathname)
  // Public marketing/catalog/legal surfaces (same as idle-probe paths).
  if (isStudentIdleProbePath(path)) return true
  if (path.startsWith('/account') || path === '/settings') return true
  if (AUTH_SELF_SERVICE.test(path)) return true
  return false
}

/**
 * Whether the current route should run auth bootstrap (session restore / OAuth callback).
 */
export function needsAuthBootstrap(pathname: string, search: string): boolean {
  const path = normalizeStudentPath(pathname)
  const params = new URLSearchParams(search)
  const code = (params.get('code') ?? '').trim()
  const state = (params.get('state') ?? '').trim()
  if (code && state) {
    return true
  }

  // Same set as isStudentIdleProbePath — public marketing/catalog/legal stay off AuthShell.
  if (isStudentIdleProbePath(path)) {
    return false
  }

  if (
    AUTH_SELF_SERVICE.test(path) ||
    path === '/dashboard' ||
    path === '/certificates' ||
    path === '/research-team/apply' ||
    path.startsWith('/account') ||
    path === '/settings' ||
    path.startsWith('/billing') ||
    path.startsWith('/checkout') ||
    LESSON_PLAYER.test(path) ||
    MODULE_QUIZ.test(path)
  ) {
    return true
  }

  return false
}
