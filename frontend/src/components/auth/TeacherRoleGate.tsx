import { useAuthenticator } from '@aws-amplify/ui-react'
import { useEffect, useState, type ReactNode } from 'react'
import { fetchMe, type UserProfile } from '../../lib/api'
import { isAuthConfigured } from '../../lib/auth'

/**
 * After Cognito sign-in, loads `/users/me` and allows only teacher or admin roles.
 */
export function TeacherRoleGate({ children }: { children: ReactNode }) {
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (authStatus !== 'authenticated') return
    let cancelled = false
    void (async () => {
      try {
        const me = await fetchMe()
        if (!cancelled) {
          setProfile(me)
          setErr(null)
        }
      } catch (e) {
        if (!cancelled) {
          setProfile(null)
          setErr(e instanceof Error ? e.message : 'Failed to load profile')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authStatus])

  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Cognito is not configured for this build. Set{' '}
        <code className="rounded bg-gray-100 px-1">VITE_COGNITO_USER_POOL_ID</code>,{' '}
        <code className="rounded bg-gray-100 px-1">VITE_COGNITO_USER_POOL_CLIENT_ID</code>, and{' '}
        <code className="rounded bg-gray-100 px-1">VITE_COGNITO_DOMAIN</code> for Google sign-in.
      </div>
    )
  }

  if (authStatus !== 'authenticated') {
    return null
  }

  if (err) {
    return <div className="p-8 text-center text-red-600">{err}</div>
  }

  if (!profile) {
    return <div className="p-8 text-center text-gray-600">Loading profile…</div>
  }

  const r = profile.role.toLowerCase()
  if (r !== 'teacher' && r !== 'admin') {
    return (
      <div className="mx-auto max-w-lg p-8 text-center">
        <h1 className="text-xl font-semibold text-gray-900">Instructor access required</h1>
        <p className="mt-2 text-gray-600">
          Your account does not have the instructor role. An admin must set the Cognito attribute{' '}
          <code className="rounded bg-gray-100 px-1">custom:role</code> to{' '}
          <code className="rounded bg-gray-100 px-1">teacher</code> (or <code className="rounded bg-gray-100 px-1">admin</code>
          ).
        </p>
      </div>
    )
  }

  return <>{children}</>
}
