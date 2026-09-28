import { signUp } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import { PasswordChecklist } from '../components/auth/PasswordChecklist'
import { useAuthenticator } from '../lib/auth-ui'
import { isAuthConfigured } from '../lib/auth'
import { isPasswordPolicyMet } from '../lib/password-policy'
import { COUNTRIES, PROFESSIONS } from '../lib/profile-options'
import { saveRegisterProfileDraft } from '../lib/register-profile-draft'
import { usePageTitle } from '../lib/page-title'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'

export default function StudentRegisterPage() {
  usePageTitle('Create account')
  const navigate = useNavigate()
  const authConfigured = isAuthConfigured()
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])

  const [givenName, setGivenName] = useState('')
  const [familyName, setFamilyName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [country, setCountry] = useState('')
  const [profession, setProfession] = useState('')
  const [institution, setInstitution] = useState('')
  const [researchInterests, setResearchInterests] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [privacyAccepted, setPrivacyAccepted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const passwordOk = useMemo(() => isPasswordPolicyMet(password), [password])
  const passwordsMatch = password.length > 0 && password === confirmPassword

  const canSubmit =
    givenName.trim() &&
    familyName.trim() &&
    email.trim() &&
    passwordOk &&
    passwordsMatch &&
    country &&
    profession &&
    termsAccepted &&
    privacyAccepted &&
    !submitting

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Registration is not available: set Cognito <code className="rounded bg-rs-sky-2 px-1">VITE_*</code> variables.
      </div>
    )
  }

  if (authStatus === 'authenticated') {
    return <Navigate to="/" replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null)
    setSubmitting(true)
    try {
      saveRegisterProfileDraft({
        email: email.trim(),
        givenName: givenName.trim(),
        familyName: familyName.trim(),
        country,
        profession,
        institution: institution.trim(),
        researchInterests: researchInterests.trim(),
        termsAccepted,
        privacyAccepted,
      })
      await signUp({
        username: email.trim(),
        password,
        options: {
          userAttributes: {
            email: email.trim(),
            given_name: givenName.trim(),
            family_name: familyName.trim(),
          },
        },
      })
      navigate(`/verify-email?email=${encodeURIComponent(email.trim())}`, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl px-5 py-12" data-testid="student-page-register">
      <Card className="p-8">
        <h1 className="text-2xl font-extrabold text-rs-ink">Create your account</h1>
        <p className="mt-2 text-sm font-semibold text-rs-body">
          Already have an account?{' '}
          <Link to="/login" className="font-bold text-rs-blue hover:underline">
            Sign in
          </Link>
        </p>

        <form className="mt-8" onSubmit={(ev) => void onSubmit(ev)}>
          <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-4">
            <Field label="First name" value={givenName} onChange={(e) => setGivenName(e.target.value)} required />
            <Field label="Last name" value={familyName} onChange={(e) => setFamilyName(e.target.value)} required />
          </div>
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Field
            label="Password"
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
              confirmPassword && !passwordsMatch ? 'Passwords must match.' : undefined
            }
            required
          />
          <Field label="Country">
            <select
              className="w-full rounded-xl border-[1.5px] border-rs-line px-[14px] py-[11px] text-[15px] font-semibold text-rs-ink"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              required
            >
              <option value="">Select country</option>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Profession">
            <select
              className="w-full rounded-xl border-[1.5px] border-rs-line px-[14px] py-[11px] text-[15px] font-semibold text-rs-ink"
              value={profession}
              onChange={(e) => setProfession(e.target.value)}
              required
            >
              <option value="">Select profession</option>
              {PROFESSIONS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Institution (optional)"
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
          />
          <Field label="Research interests (optional)">
            <textarea
              className="min-h-[88px] w-full rounded-xl border-[1.5px] border-rs-line px-[14px] py-[11px] text-[15px] font-semibold text-rs-ink"
              value={researchInterests}
              onChange={(e) => setResearchInterests(e.target.value)}
            />
          </Field>

          <label className="mb-3 flex items-start gap-2 text-sm font-semibold text-rs-body">
            <input
              type="checkbox"
              checked={termsAccepted}
              onChange={(e) => setTermsAccepted(e.target.checked)}
              className="mt-1"
            />
            <span>
              I agree to the{' '}
              <Link to="/terms" className="font-bold text-rs-blue hover:underline">
                Terms of Service
              </Link>
            </span>
          </label>
          <label className="mb-6 flex items-start gap-2 text-sm font-semibold text-rs-body">
            <input
              type="checkbox"
              checked={privacyAccepted}
              onChange={(e) => setPrivacyAccepted(e.target.checked)}
              className="mt-1"
            />
            <span>
              I agree to the{' '}
              <Link to="/privacy" className="font-bold text-rs-blue hover:underline">
                Privacy Policy
              </Link>
            </span>
          </label>

          {error ? (
            <p className="mb-3 text-sm font-semibold text-red-700" role="alert">
              {error}
            </p>
          ) : null}

          <Button type="submit" className="w-full" disabled={!canSubmit} data-testid="register-submit">
            Create account
          </Button>
        </form>
      </Card>
    </div>
  )
}
