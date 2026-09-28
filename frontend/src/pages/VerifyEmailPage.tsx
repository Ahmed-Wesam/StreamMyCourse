import { confirmSignUp, fetchAuthSession, signIn } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'

import { patchUsersMe } from '../lib/api/session'
import { isAuthConfigured } from '../lib/auth'
import {
  clearRegisterProfileDraft,
  readRegisterProfileDraft,
  REGISTER_PROFILE_DRAFT_KEY,
} from '../lib/register-profile-draft'
import { usePageTitle } from '../lib/page-title'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'

export default function VerifyEmailPage() {
  usePageTitle('Verify email')
  const [params] = useSearchParams()
  const emailFromQuery = (params.get('email') ?? '').trim()
  const draft = readRegisterProfileDraft()
  const email = emailFromQuery || draft?.email || ''

  const authConfigured = isAuthConfigured()

  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Email verification requires Cognito configuration.
      </div>
    )
  }

  if (done) {
    return <Navigate to="/account/profile" replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!email || !code.trim() || !password) {
      setError('Enter the verification code and your password.')
      return
    }
    const profileDraft = readRegisterProfileDraft()
    if (!profileDraft) {
      setError('Registration details expired. Please register again.')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await confirmSignUp({ username: email, confirmationCode: code.trim() })
      await signIn({ username: email, password })
      const now = new Date().toISOString()
      await patchUsersMe({
        givenName: profileDraft.givenName,
        familyName: profileDraft.familyName,
        country: profileDraft.country,
        profession: profileDraft.profession,
        institution: profileDraft.institution || undefined,
        researchInterests: profileDraft.researchInterests || undefined,
        termsAcceptedAt: now,
        privacyAcceptedAt: now,
      })
      await fetchAuthSession({ forceRefresh: true })
      clearRegisterProfileDraft()
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-5 py-12" data-testid="student-page-verify-email">
      <Card className="p-8">
        <h1 className="text-2xl font-extrabold text-rs-ink">Verify your email</h1>
        <p className="mt-2 text-sm font-semibold text-rs-body">
          We sent a code to <strong>{email || 'your email'}</strong>.
        </p>
        <form className="mt-6" onSubmit={(ev) => void onSubmit(ev)}>
          <Field
            label="Verification code"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          <Field
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error ? (
            <p className="mb-3 text-sm font-semibold text-red-700" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={submitting}>
            Verify and continue
          </Button>
        </form>
        <p className="mt-4 text-center text-sm font-semibold text-rs-body">
          <Link to="/login" className="font-bold text-rs-blue hover:underline">
            Back to sign in
          </Link>
        </p>
        {/* Test hook: draft key must never store password */}
        <span data-testid="register-draft-key" hidden>
          {REGISTER_PROFILE_DRAFT_KEY}
        </span>
      </Card>
    </div>
  )
}
