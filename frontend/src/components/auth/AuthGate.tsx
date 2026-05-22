import { lazy, Suspense, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

import { needsAuthBootstrap } from '../../lib/auth-bootstrap'
import { RouteChunkFallback } from '../layout/RouteChunkFallback'

const AuthShell = lazy(() => import('./AuthShell'))

export function AuthGate({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation()

  if (!needsAuthBootstrap(pathname, search)) {
    return <>{children}</>
  }

  return (
    <Suspense fallback={<RouteChunkFallback />}>
      <AuthShell>{children}</AuthShell>
    </Suspense>
  )
}
