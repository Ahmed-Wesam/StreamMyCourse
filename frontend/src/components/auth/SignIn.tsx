import { signIn, signInWithRedirect } from 'aws-amplify/auth'
import type { FormEvent, ReactNode } from 'react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuthenticator } from '../../lib/auth-ui'
import { loginAuthCard } from '../../lib/marketing/loginCopy'
import { persistReturnPathBeforeHostedUi } from '../../lib/post-login-return'
import { usePageTitle } from '../../lib/page-title'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'

export const GOOGLE_SIGN_IN_LABEL = 'Continue with Google'

type SignInProps = {
  children?: ReactNode
  /** Teacher app: Google only. Student login page: email + password + Google. */
  variant?: 'student' | 'teacher'
  /**
   * When true, render only the card (login page supplies the surrounding layout).
   * Gate routes leave this false so the form is centered with a max width.
   */
  embedded?: boolean
}

function GoogleIcon() {
  return (
    <svg className="size-5 shrink-0" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  )
}

function SignInFormChrome({
  embedded,
  children,
}: {
  embedded?: boolean
  children: ReactNode
}) {
  if (embedded) return <>{children}</>
  return (
    <div
      className="flex min-h-[calc(100vh-4rem)] justify-center bg-gradient-to-b from-rs-sky-2 to-white px-5 py-12 sm:px-7 sm:py-16"
      data-testid="signin-page-chrome"
    >
      {children}
    </div>
  )
}

function AuthCardShell({ children }: { children: ReactNode }) {
  return (
    <div
      className="relative mx-auto w-full max-w-[420px] overflow-hidden rounded-[24px] border border-rs-line bg-white p-8 shadow-rs-lg sm:p-[30px]"
      data-testid="login-auth-card"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(480px_220px_at_100%_0%,rgba(30,94,255,.04),transparent)]"
      />
      <div className="relative">{children}</div>
    </div>
  )
}

function SignInConfiguring({ embedded }: { embedded?: boolean }) {
  usePageTitle('Sign in')
  return (
    <SignInFormChrome embedded={embedded}>
      <AuthCardShell>
        <div role="status" aria-live="polite" className="py-4 text-center">
          <p className="text-sm font-semibold text-rs-body">Signing you in…</p>
          <div className="mx-auto mt-4 h-1.5 w-40 overflow-hidden rounded-full bg-rs-sky-2">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-rs-blue/80" />
          </div>
        </div>
      </AuthCardShell>
    </SignInFormChrome>
  )
}

function TeacherSignInForm({ embedded }: { embedded?: boolean }) {
  usePageTitle('Sign in')
  return (
    <SignInFormChrome embedded={embedded}>
      <AuthCardShell>
        <h2 className="text-lg font-extrabold tracking-tight text-rs-ink">{loginAuthCard.title}</h2>
        <p className="mt-1 text-sm font-semibold text-rs-muted">{loginAuthCard.sub}</p>
        <div className="mt-6 flex flex-col gap-2.5">
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => {
              persistReturnPathBeforeHostedUi()
              void signInWithRedirect({ provider: 'Google' })
            }}
          >
            <GoogleIcon />
            {GOOGLE_SIGN_IN_LABEL}
          </Button>
        </div>
        <div className="my-5 h-px bg-rs-line" aria-hidden />
        <p className="text-center text-sm font-semibold text-rs-body">
          By continuing, you agree to our use of authentication cookies for this session.
        </p>
      </AuthCardShell>
    </SignInFormChrome>
  )
}

function StudentSignInForm({ embedded }: { embedded?: boolean }) {
  usePageTitle('Sign in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!email.trim() || !password) {
      setError('Enter your email and password.')
      return
    }
    setSubmitting(true)
    try {
      await signIn({ username: email.trim(), password })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SignInFormChrome embedded={embedded}>
      <AuthCardShell>
        <h2 className="text-lg font-extrabold tracking-tight text-rs-ink">{loginAuthCard.title}</h2>
        <p className="mt-1 text-sm font-semibold text-rs-muted">{loginAuthCard.sub}</p>

        <form className="mt-6 space-y-1" onSubmit={(e) => void onSubmit(e)}>
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
          />
          <Field
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
          />
          <p className="mb-4 text-right">
            <Link to="/forgot-password" className="text-sm font-bold text-rs-blue hover:underline">
              Forgot password?
            </Link>
          </p>
          {error ? (
            <p className="mb-3 text-sm font-semibold text-red-700" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={submitting}>
            Sign in
          </Button>
        </form>

        <div className="my-5 flex items-center gap-3" aria-hidden>
          <div className="h-px flex-1 bg-rs-line" />
          <span className="text-xs font-bold uppercase tracking-wide text-rs-muted">or</span>
          <div className="h-px flex-1 bg-rs-line" />
        </div>

        <Button
          type="button"
          variant="ghost"
          className="w-full"
          onClick={() => {
            persistReturnPathBeforeHostedUi()
            void signInWithRedirect({ provider: 'Google' })
          }}
        >
          <GoogleIcon />
          {GOOGLE_SIGN_IN_LABEL}
        </Button>

        <p className="mt-5 text-center text-sm font-semibold text-rs-body">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="font-bold text-rs-blue hover:underline">
            Create Account
          </Link>
        </p>
      </AuthCardShell>
    </SignInFormChrome>
  )
}

export function SignIn({ children, variant = 'student', embedded = false }: SignInProps) {
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])

  if (authStatus === 'authenticated') {
    return <>{children}</>
  }

  if (authStatus === 'configuring') {
    return <SignInConfiguring embedded={embedded} />
  }

  if (variant === 'teacher') {
    return <TeacherSignInForm embedded={embedded} />
  }

  return <StudentSignInForm embedded={embedded} />
}
