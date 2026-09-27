import { useAuthenticator } from '../../lib/auth-ui'
import { useEffect, useState, type ReactNode } from 'react'
import { ApiError } from '../../lib/api/client'
import { fetchMe } from '../../lib/api/session'
import type { UserProfile } from '../../lib/api/types'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { isAuthConfigured } from '../../lib/auth'
import { legalConfig } from '../../lib/legalConfig'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'

function InstructorAccessPanel({
  title,
  body,
  signOut,
}: {
  title: string
  body: ReactNode
  signOut: () => void
}) {
  return (
    <div className="mx-auto max-w-lg px-4 py-8 text-rs-ink sm:px-6">
      <Card className="p-8 text-center">
        <h1 className="text-xl font-extrabold text-rs-navy">{title}</h1>
        <p className="mt-2 text-rs-body">{body}</p>
        <Button type="button" variant="ghost" className="mt-6" onClick={() => void signOut()}>
          Sign out
        </Button>
      </Card>
    </div>
  )
}

function SupportMailtoLink() {
  return (
    <a
      className="font-semibold text-rs-blue hover:underline"
      href={`mailto:${legalConfig.supportEmail}`}
    >
      {legalConfig.supportEmail}
    </a>
  )
}

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
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Cognito is not configured for this build. Set{' '}
        <code className="rounded bg-rs-sky-2 px-1">VITE_COGNITO_USER_POOL_ID</code>,{' '}
        <code className="rounded bg-rs-sky-2 px-1">VITE_COGNITO_USER_POOL_CLIENT_ID</code>, and{' '}
        <code className="rounded bg-rs-sky-2 px-1">VITE_COGNITO_DOMAIN</code> for Google sign-in.
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
        <InstructorAccessPanel
          title="Sign-in required"
          signOut={signOut}
          body={
            <>
              Your session may have expired. Please sign out and sign in again. If the problem continues, contact{' '}
              <SupportMailtoLink />.
            </>
          }
        />
      )
    }

    if (err instanceof ApiError && err.status === 403) {
      return (
        <InstructorAccessPanel
          title="Instructor access required"
          signOut={signOut}
          body={
            <>
              This account doesn’t have access to the Instructor Dashboard. If you believe this is a mistake, please
              contact <SupportMailtoLink />.
            </>
          }
        />
      )
    }

    const msg = catalogApiUserMessage(err, 'loadProfile')
    return <div className="p-8 text-center text-red-600">{msg}</div>
  }

  if (!profile) {
    return <div className="p-8 text-center text-rs-muted">Loading profile…</div>
  }

  const r = profile.role.toLowerCase()
  if (r !== 'teacher' && r !== 'admin') {
    return (
      <InstructorAccessPanel
        title="Instructor access required"
        signOut={signOut}
        body={
          <>
            This account doesn’t have access to the Instructor Dashboard. If you believe this is a mistake, please
            contact <SupportMailtoLink />.
          </>
        }
      />
    )
  }

  return <>{children}</>
}
