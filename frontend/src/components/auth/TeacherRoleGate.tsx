import { useAuthenticator } from '@aws-amplify/ui-react'
import { useEffect, useState, type ReactNode } from 'react'
import { ApiError, fetchMe, type UserProfile } from '../../lib/api'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { isAuthConfigured } from '../../lib/auth'

/**
 * After Cognito sign-in, loads `/users/me` and allows only teacher or admin roles.
 */
export function TeacherRoleGate({ children }: { children: ReactNode }) {
  const { authStatus, signOut } = useAuthenticator((ctx) => [ctx.authStatus, ctx.signOut])
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [err, setErr] = useState<unknown>(null)

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
          setErr(e)
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
    // For auth/permission errors from /users/me:
    // - 401: session not valid → prompt sign-in again (avoids masking auth wiring issues as "no instructor access").
    // - 403: signed in but not allowed → show instructor access message.
    if (err instanceof ApiError && err.status === 401) {
      return (
        <div className="mx-auto max-w-lg p-8 text-center">
          <h1 className="text-xl font-semibold text-gray-900">Sign-in required</h1>
          <p className="mt-2 text-gray-600">
            Your session may have expired. Please sign out and sign in again. If the problem continues, contact{' '}
            <a className="font-medium text-emerald-700 hover:text-emerald-800" href="mailto:streammycourse@gmail.com">
              streammycourse@gmail.com
            </a>
            .
          </p>
          <button
            type="button"
            className="mt-6 inline-flex min-h-[44px] items-center justify-center rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 active:bg-emerald-100"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
        </div>
      )
    }

    if (err instanceof ApiError && err.status === 403) {
      return (
        <div className="mx-auto max-w-lg p-8 text-center">
          <h1 className="text-xl font-semibold text-gray-900">Instructor access required</h1>
          <p className="mt-2 text-gray-600">
            This account doesn’t have access to the Instructor Dashboard. If you believe this is a mistake, please
            contact{' '}
            <a className="font-medium text-emerald-700 hover:text-emerald-800" href="mailto:streammycourse@gmail.com">
              streammycourse@gmail.com
            </a>
            .
          </p>
          <button
            type="button"
            className="mt-6 inline-flex min-h-[44px] items-center justify-center rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 active:bg-emerald-100"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
        </div>
      )
    }

    const msg = catalogApiUserMessage(err, 'loadProfile')
    return <div className="p-8 text-center text-red-600">{msg}</div>
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
          This account doesn’t have access to the Instructor Dashboard. If you believe this is a mistake, please
          contact{' '}
          <a className="font-medium text-emerald-700 hover:text-emerald-800" href="mailto:streammycourse@gmail.com">
            streammycourse@gmail.com
          </a>
          .
        </p>
        <button
          type="button"
          className="mt-6 inline-flex min-h-[44px] items-center justify-center rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 active:bg-emerald-100"
          onClick={() => void signOut()}
        >
          Sign out
        </button>
      </div>
    )
  }

  return <>{children}</>
}
