import { confirmResetPassword } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { PasswordChecklist } from '../components/auth/PasswordChecklist'
import { isAuthConfigured } from '../lib/auth'
import { isPasswordPolicyMet } from '../lib/password-policy'
import { usePageTitle } from '../lib/page-title'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'

export default function ResetPasswordPage() {
  usePageTitle('Reset password')
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const emailDefault = (params.get('email') ?? '').trim()

  const authConfigured = isAuthConfigured()
  const [email, setEmail] = useState(emailDefault)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Password reset requires Cognito configuration.
      </div>
    )
  }

  const passwordOk = isPasswordPolicyMet(password)
  const canSubmit =
    email.trim() && code.trim() && passwordOk && password === confirmPassword && !submitting

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null)
    setSubmitting(true)
    try {
      await confirmResetPassword({
        username: email.trim(),
        confirmationCode: code.trim(),
        newPassword: password,
      })
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-5 py-12" data-testid="student-page-reset-password">
      <Card className="p-8">
        <h1 className="text-2xl font-extrabold text-rs-ink">Set a new password</h1>
        <form className="mt-6" onSubmit={(ev) => void onSubmit(ev)}>
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Field
            label="Verification code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          <Field
            label="New password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <PasswordChecklist password={password} />
          <Field
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={
              confirmPassword && password !== confirmPassword ? 'Passwords must match.' : undefined
            }
            required
          />
          {error ? (
            <p className="mb-3 text-sm font-semibold text-red-700" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={!canSubmit}>
            Update password
          </Button>
        </form>
        <p className="mt-4 text-center text-sm font-semibold text-rs-body">
          <Link to="/login" className="font-bold text-rs-blue hover:underline">
            Back to sign in
          </Link>
        </p>
      </Card>
    </div>
  )
}
