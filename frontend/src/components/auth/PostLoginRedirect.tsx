import { useAuthenticator } from '@aws-amplify/ui-react'
import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { POST_LOGIN_RETURN_TO_KEY, sanitizeReturnPath } from '../../lib/post-login-return'

/**
 * After Hosted UI returns to `/`, restores a previously stored in-SPA path.
 */
export function PostLoginRedirect() {
  const navigate = useNavigate()
  const location = useLocation()
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])
  useEffect(() => {
    if (authStatus !== 'authenticated') return

    const raw = sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)
    if (!raw) return

    const to = sanitizeReturnPath(raw)
    if (!to) {
      sessionStorage.removeItem(POST_LOGIN_RETURN_TO_KEY)
      return
    }

    const here = `${location.pathname}${location.search}${location.hash}`
    if (to === here) {
      sessionStorage.removeItem(POST_LOGIN_RETURN_TO_KEY)
      return
    }

    void navigate(to, { replace: true })
  }, [authStatus, location.pathname, location.search, location.hash, navigate])

  return null
}
