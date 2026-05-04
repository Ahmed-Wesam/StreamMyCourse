import type { ReactNode } from 'react'
import { TeacherRoleGate } from './TeacherRoleGate'

/** Instructor dashboard shell: Cognito sign-in + teacher/admin role from `/users/me`. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  return <TeacherRoleGate>{children}</TeacherRoleGate>
}
