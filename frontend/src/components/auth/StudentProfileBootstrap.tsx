import { useAuthenticator } from '../../lib/auth-ui'
import { useEffect, useRef } from 'react'

/**
 * On student sign-in, warms the user profile via GET /users/me once per session.
 * Redundant when Cognito PostAuthentication sync is deployed but improves first-paint UX.
 */
export function StudentProfileBootstrap() {
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])
  const didFetch = useRef(false)

  useEffect(() => {
    if (authStatus !== 'authenticated') {
      didFetch.current = false
      return
    }
    if (didFetch.current) {
      return
    }
    didFetch.current = true
    void (async () => {
      const { fetchMe } = await import('../../lib/api/session')
      const { markUserProfileWarmed } = await import('../../lib/auth-session-lazy')
      await fetchMe()
      markUserProfileWarmed()
    })().catch(() => {
      // Non-fatal: Cognito trigger or a later /users/me may still provision the row.
    })
  }, [authStatus])

  return null
}
