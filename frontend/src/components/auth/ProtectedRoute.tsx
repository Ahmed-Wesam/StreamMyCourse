import { lazy, Suspense, type ReactNode } from 'react'

import { RouteChunkFallback } from '../layout/RouteChunkFallback'

const TeacherRoleGate = lazy(() =>
  import('./TeacherRoleGate').then((mod) => ({ default: mod.TeacherRoleGate })),
)

/** Instructor dashboard shell: Cognito sign-in + teacher/admin role from `/users/me`. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<RouteChunkFallback />}>
      <TeacherRoleGate>{children}</TeacherRoleGate>
    </Suspense>
  )
}
