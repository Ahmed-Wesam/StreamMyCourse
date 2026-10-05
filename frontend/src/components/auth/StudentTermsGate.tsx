import { useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { fetchMe, hasSignedInIdToken } from '../../lib/api/session'
import { isStudentTermsGateExemptPath } from '../../lib/auth-bootstrap'

type GateState = 'idle' | 'checking' | 'ready' | 'redirect'

export function StudentTermsGate({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [state, setState] = useState<GateState>('idle')

  useEffect(() => {
    if (isStudentTermsGateExemptPath(pathname)) {
      setState('ready')
      return
    }

    let cancelled = false
    setState('checking')

    void (async () => {
      const signedIn = await hasSignedInIdToken()
      if (cancelled) return
      if (!signedIn) {
        setState('ready')
        return
      }
      try {
        const profile = await fetchMe()
        if (cancelled) return
        const termsOk = Boolean(profile.termsAcceptedAt?.trim())
        const privacyOk = Boolean(profile.privacyAcceptedAt?.trim())
        if (!termsOk || !privacyOk) {
          setState('redirect')
          return
        }
      } catch {
        // Do not trap the site on profile when /users/me is unavailable.
        if (!cancelled) setState('ready')
        return
      }
      if (!cancelled) setState('ready')
    })()

    return () => {
      cancelled = true
    }
  }, [pathname])

  if (state === 'checking') {
    return null
  }

  if (state === 'redirect') {
    return <Navigate to="/account/profile" replace />
  }

  return <>{children}</>
}
