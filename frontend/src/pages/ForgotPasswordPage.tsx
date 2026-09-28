import { resetPassword } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { isAuthConfigured } from '../lib/auth'
import { usePageTitle } from '../lib/page-title'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'

const GENERIC_SUCCESS =
  'If an account exists for that email, we sent password reset instructions. Check your inbox and spam folder.'

export default function ForgotPasswordPage() {
  usePageTitle('Forgot password')
  const authConfigured = isAuthConfigured()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Password reset requires Cognito configuration.
      </div>
    )
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setSubmitting(true)
    try {
      await resetPassword({ username: email.trim() })
    } catch {
      /* same success UI for user-not-found style errors */
    } finally {
      setSent(true)
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-5 py-12" data-testid="student-page-forgot-password">
      <Card className="p-8">
        <h1 className="text-2xl font-extrabold text-rs-ink">Forgot password</h1>
        {sent ? (
          <p className="mt-4 text-sm font-semibold leading-relaxed text-rs-body" role="status">
            {GENERIC_SUCCESS}
          </p>
        ) : (
          <>
            <p className="mt-2 text-sm font-semibold text-rs-body">
              Enter your email and we will send reset instructions.
            </p>
            <form className="mt-6" onSubmit={(ev) => void onSubmit(ev)}>
              <Field
                label="Email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Button type="submit" className="w-full" disabled={submitting}>
                Send reset link
              </Button>
            </form>
          </>
        )}
        <p className="mt-6 text-center text-sm font-semibold text-rs-body">
          <Link to="/login" className="font-bold text-rs-blue hover:underline">
            Back to sign in
          </Link>
        </p>
      </Card>
    </div>
  )
}
