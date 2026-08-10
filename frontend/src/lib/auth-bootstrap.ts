const COURSE_DETAIL = /^\/courses\/[^/]+$/
const LESSON_PLAYER = /^\/courses\/[^/]+\/lessons\//
const MODULE_QUIZ = /^\/courses\/[^/]+\/modules\/[^/]+\/quiz/

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

  if (
    pathname === '/' ||
    pathname === '/details' ||
    pathname === '/learn' ||
    pathname === '/courses' ||
    pathname === '/terms' ||
    pathname === '/privacy' ||
    pathname === '/refund' ||
    pathname === '/delivery' ||
    pathname === '/educational-disclaimer' ||
    COURSE_DETAIL.test(pathname)
  ) {
    return false
  }

  if (
    pathname.startsWith('/login') ||
    pathname.startsWith('/account') ||
    pathname.startsWith('/billing') ||
    LESSON_PLAYER.test(pathname) ||
    MODULE_QUIZ.test(pathname)
  ) {
    return true
  }

  return false
}
