import { fetchAuthSession, updatePassword, updateUserAttributes } from 'aws-amplify/auth'
import { Lock, User, Bell } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { fetchMe, patchUsersMe } from '../../lib/api/session'
import type { UserProfile } from '../../lib/api/types'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { isNativeCognitoPasswordUser } from '../../lib/cognito-native-user'
import { isPasswordPolicyMet } from '../../lib/password-policy'
import { COUNTRIES, PROFESSIONS } from '../../lib/profile-options'
import { usePageTitle } from '../../lib/page-title'
import { shouldSuppressInlineSessionSupersededMessage } from '../../lib/session-superseded-inline'
import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { PasswordChecklist } from '../../components/auth/PasswordChecklist'

type ProfileState =
  | { status: 'loading' }
  | { status: 'superseded' }
  | { status: 'error'; message: string }
  | { status: 'ready'; profile: UserProfile }

function AcctCardTitle({ icon: Icon, children }: { icon: typeof User; children: string }) {
  return (
    <h3 className="mb-5 flex items-center gap-2.5 text-[17px] font-extrabold tracking-tight text-rs-ink">
      <span className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] border border-[#e2ebff] bg-rs-sky-2 text-rs-blue">
        <Icon aria-hidden className="size-4" strokeWidth={2} />
      </span>
      {children}
    </h3>
  )
}

function AcctCard({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-[22px] border border-rs-line bg-white p-7 shadow-rs-sm sm:px-[30px]">{children}</div>
  )
}

export default function AccountProfilePage() {
  usePageTitle('Account')
  const [state, setState] = useState<ProfileState>({ status: 'loading' })
  const [givenName, setGivenName] = useState('')
  const [familyName, setFamilyName] = useState('')
  const [country, setCountry] = useState('')
  const [profession, setProfession] = useState('')
  const [institution, setInstitution] = useState('')
  const [researchInterests, setResearchInterests] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [privacyAccepted, setPrivacyAccepted] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [nativePasswordUser, setNativePasswordUser] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const profile = await fetchMe()
        if (cancelled) return
        setGivenName(profile.givenName ?? '')
        setFamilyName(profile.familyName ?? '')
        setCountry(profile.country ?? '')
        setProfession(profile.profession ?? '')
        setInstitution(profile.institution ?? '')
        setResearchInterests(profile.researchInterests ?? '')
        setTermsAccepted(Boolean(profile.termsAcceptedAt?.trim()))
        setPrivacyAccepted(Boolean(profile.privacyAcceptedAt?.trim()))
        setState({ status: 'ready', profile })
        const session = await fetchAuthSession()
        const payload = session.tokens?.idToken?.payload as Record<string, unknown> | undefined
        if (!cancelled) setNativePasswordUser(isNativeCognitoPasswordUser(payload))
      } catch (err) {
        if (cancelled) return
        if (shouldSuppressInlineSessionSupersededMessage(err)) {
          setState({ status: 'superseded' })
          return
        }
        setState({ status: 'error', message: catalogApiUserMessage(err) })
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const needsTermsUi = useMemo(() => {
    if (state.status !== 'ready') return false
    return !state.profile.termsAcceptedAt?.trim() || !state.profile.privacyAcceptedAt?.trim()
  }, [state])

  async function onSaveProfile(e: FormEvent) {
    e.preventDefault()
    if (state.status !== 'ready') return
    if (!country || !profession) {
      setSaveError('Country and profession are required.')
      return
    }
    if (needsTermsUi && (!termsAccepted || !privacyAccepted)) {
      setSaveError('Accept the Terms of Service and Privacy Policy to continue.')
      return
    }
    setSaveError(null)
    setSaveMessage(null)
    setSaving(true)
    const now = new Date().toISOString()
    try {
      await updateUserAttributes({
        userAttributes: {
          given_name: givenName.trim(),
          family_name: familyName.trim(),
        },
      })
      const updated = await patchUsersMe({
        givenName: givenName.trim(),
        familyName: familyName.trim(),
        country,
        profession,
        institution: institution.trim() || undefined,
        researchInterests: researchInterests.trim() || undefined,
        termsAcceptedAt: termsAccepted ? state.profile.termsAcceptedAt?.trim() || now : now,
        privacyAcceptedAt: privacyAccepted ? state.profile.privacyAcceptedAt?.trim() || now : now,
      })
      await fetchAuthSession({ forceRefresh: true })
      setState({ status: 'ready', profile: updated })
      setSaveMessage('Profile saved.')
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : catalogApiUserMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function onChangePassword(e: FormEvent) {
    e.preventDefault()
    if (!nativePasswordUser) return
    if (!isPasswordPolicyMet(newPassword) || newPassword !== confirmNewPassword) {
      setPasswordError('Choose a valid password that matches confirmation.')
      return
    }
    setPasswordError(null)
    setPasswordMessage(null)
    setChangingPassword(true)
    try {
      await updatePassword({ oldPassword: currentPassword, newPassword })
      setPasswordMessage('Password updated.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Could not update password.')
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <section aria-labelledby="account-profile-heading" className="space-y-6">
      <div>
        <h2 id="account-profile-heading" className="text-xl font-extrabold text-rs-ink">
          Profile
        </h2>
        <p className="mt-1 text-sm font-semibold text-rs-body">Manage your account details.</p>
      </div>

      {state.status === 'loading' ? (
        <p className="text-sm font-semibold text-rs-muted" role="status">
          Loading profile…
        </p>
      ) : null}

      {state.status === 'superseded' ? (
        <p className="text-sm font-semibold text-rs-muted" role="status">
          Sign in again using the message above to view your profile.
        </p>
      ) : null}

      {state.status === 'error' ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800"
          role="alert"
        >
          {state.message}
        </p>
      ) : null}

      {state.status === 'ready' ? (
        <>
          <AcctCard>
            <AcctCardTitle icon={User}>Profile Information</AcctCardTitle>
            <form onSubmit={(ev) => void onSaveProfile(ev)}>
              <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-4">
                <Field label="First name" value={givenName} onChange={(e) => setGivenName(e.target.value)} />
                <Field label="Last name" value={familyName} onChange={(e) => setFamilyName(e.target.value)} />
              </div>
              <Field label="Email" value={state.profile.email} readOnly aria-readonly />
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

              {needsTermsUi ? (
                <>
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
                  <label className="mb-4 flex items-start gap-2 text-sm font-semibold text-rs-body">
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
                </>
              ) : null}

              {saveError ? (
                <p className="mb-3 text-sm font-semibold text-red-700" role="alert">
                  {saveError}
                </p>
              ) : null}
              {saveMessage ? (
                <p className="mb-3 text-sm font-semibold text-emerald-700" role="status">
                  {saveMessage}
                </p>
              ) : null}
              <Button type="submit" disabled={saving}>
                Save profile
              </Button>
            </form>
          </AcctCard>

          {nativePasswordUser ? (
            <AcctCard>
              <AcctCardTitle icon={Lock}>Change password</AcctCardTitle>
              <form onSubmit={(ev) => void onChangePassword(ev)}>
                <Field
                  label="Current password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
                <Field
                  label="New password"
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <PasswordChecklist password={newPassword} />
                <Field
                  label="Confirm new password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                />
                {passwordError ? (
                  <p className="mb-3 text-sm font-semibold text-red-700" role="alert">
                    {passwordError}
                  </p>
                ) : null}
                {passwordMessage ? (
                  <p className="mb-3 text-sm font-semibold text-emerald-700" role="status">
                    {passwordMessage}
                  </p>
                ) : null}
                <Button type="submit" disabled={changingPassword}>
                  Update password
                </Button>
              </form>
            </AcctCard>
          ) : (
            <AcctCard>
              <AcctCardTitle icon={Lock}>Security</AcctCardTitle>
              <p className="text-sm font-semibold leading-relaxed text-rs-body">
                You signed in with Google. Password changes are not available for this account.
              </p>
            </AcctCard>
          )}

          <AcctCard>
            <AcctCardTitle icon={Bell}>Notification Preferences</AcctCardTitle>
            <p className="text-[12.5px] font-semibold leading-relaxed text-rs-muted">
              Course announcements, quiz results, certificates, Research Team updates, and product updates will be
              configurable here. Preferences are not editable in this release.
            </p>
          </AcctCard>
        </>
      ) : null}
    </section>
  )
}
