import { fetchAuthSession, updatePassword, updateUserAttributes } from 'aws-amplify/auth'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { fetchMe, patchUsersMe } from '../../lib/api/session'
import type { UserProfile } from '../../lib/api/types'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { isNativeCognitoPasswordUser } from '../../lib/cognito-native-user'
import { isPasswordPolicyMet, passwordChecks, type PasswordCheckId } from '../../lib/password-policy'
import { COUNTRIES, PROFESSIONS } from '../../lib/profile-options'
import { usePageTitle } from '../../lib/page-title'
import { shouldSuppressInlineSessionSupersededMessage } from '../../lib/session-superseded-inline'
import { IconBell, IconCheck, IconLock, IconUser } from './accountIcons'
import './AccountPage.css'

type ProfileState =
  | { status: 'loading' }
  | { status: 'superseded' }
  | { status: 'error'; message: string }
  | { status: 'ready'; profile: UserProfile }

const PW_ORDER: PasswordCheckId[] = ['length', 'upper', 'lower', 'number']
const PW_LABELS: Record<PasswordCheckId, string> = {
  length: '8+ characters',
  upper: 'Uppercase',
  lower: 'Lowercase',
  number: 'Number',
}

const NOTIFICATION_ROWS = [
  { key: 'courseAnnouncements', title: 'Course Announcements', detail: 'Updates and announcements from your enrolled courses.' },
  { key: 'quizResults', title: 'Quiz Results', detail: 'Notifications when your quiz submissions are graded.' },
  { key: 'certificateAwards', title: 'Certificate Awards', detail: 'Celebrate when you earn a new certificate.' },
  { key: 'teamUpdates', title: 'Research Team Updates', detail: 'News about the Research Spectrum Research Team pathway.' },
  { key: 'productUpdates', title: 'Product Updates', detail: 'Feature releases and platform improvements.' },
] as const

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
        const googleTermsAck = (await import('../../lib/google-oauth-terms')).readGoogleOAuthTermsAck()
        setTermsAccepted(Boolean(profile.termsAcceptedAt?.trim()) || Boolean(googleTermsAck))
        setPrivacyAccepted(Boolean(profile.privacyAcceptedAt?.trim()) || Boolean(googleTermsAck))
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

  const pwChecks = passwordChecks(newPassword)

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
      const { clearGoogleOAuthTermsAck } = await import('../../lib/google-oauth-terms')
      clearGoogleOAuthTermsAck()
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

  if (state.status === 'loading') {
    return (
      <section className="db" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <p className="field-hint" role="status">
            Loading profile…
          </p>
        </div>
      </section>
    )
  }

  if (state.status === 'superseded') {
    return (
      <section className="db" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <p className="field-hint" role="status">
            Sign in again using the message above to view your profile.
          </p>
        </div>
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section className="db" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <p className="save-error" role="alert">
            {state.message}
          </p>
        </div>
      </section>
    )
  }

  return (
    <>
      <div className="section-sep">
        <div className="wrap">
          <div className="section-group-header">
            <span className="sg-label">
              <IconUser />
              Account
            </span>
          </div>
        </div>
      </div>

      <section className="db" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <div className="acct-card reveal">
            <h3 className="acct-card-title">
              <span className="act-ic">
                <IconUser />
              </span>
              Profile Information
            </h3>
            <form onSubmit={(ev) => void onSaveProfile(ev)}>
              <div className="field-grid">
                <div className="field">
                  <label htmlFor="acct-first-name">First Name</label>
                  <input
                    type="text"
                    id="acct-first-name"
                    placeholder="First name"
                    value={givenName}
                    onChange={(e) => setGivenName(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="acct-last-name">Last Name</label>
                  <input
                    type="text"
                    id="acct-last-name"
                    placeholder="Last name"
                    value={familyName}
                    onChange={(e) => setFamilyName(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="acct-email">Email Address</label>
                  <input type="email" id="acct-email" readOnly aria-readonly value={state.profile.email} />
                  <p className="field-hint">Used for login and certificate delivery.</p>
                </div>
                <div className="field">
                  <label htmlFor="acct-country">Country</label>
                  <select id="acct-country" value={country} onChange={(e) => setCountry(e.target.value)} required>
                    <option value="">Select country</option>
                    {COUNTRIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="acct-profession">Profession</label>
                  <select
                    id="acct-profession"
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
                </div>
                <div className="field">
                  <label htmlFor="acct-institution">Institution</label>
                  <input
                    type="text"
                    id="acct-institution"
                    placeholder="Hospital or university"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                  />
                  {!institution.trim() ? <p className="field-hint">Not provided</p> : null}
                </div>
              </div>
              <div className="field" style={{ marginBottom: 20 }}>
                <label htmlFor="acct-interests">Research Interests</label>
                <input
                  type="text"
                  id="acct-interests"
                  placeholder="e.g. Cardiology, Breast Cancer, Surgical Oncology, AI"
                  value={researchInterests}
                  onChange={(e) => setResearchInterests(e.target.value)}
                />
                <p className="field-hint">
                  Specific research topics that define your expertise. These appear on your profile and Research Team
                  application. To set research project type preferences, visit{' '}
                  <Link to="/settings" style={{ color: 'var(--blue)' }}>
                    Settings → Research Preferences
                  </Link>
                  .
                </p>
              </div>

              {needsTermsUi ? (
                <>
                  <label className="terms-row">
                    <input
                      type="checkbox"
                      checked={termsAccepted}
                      onChange={(e) => setTermsAccepted(e.target.checked)}
                    />
                    <span>
                      I agree to the{' '}
                      <Link to="/terms">Terms of Service</Link>
                    </span>
                  </label>
                  <label className="terms-row">
                    <input
                      type="checkbox"
                      checked={privacyAccepted}
                      onChange={(e) => setPrivacyAccepted(e.target.checked)}
                    />
                    <span>
                      I agree to the{' '}
                      <Link to="/privacy">Privacy Policy</Link>
                    </span>
                  </label>
                </>
              ) : null}

              {saveError ? (
                <p className="save-error" role="alert">
                  {saveError}
                </p>
              ) : null}
              <div className="save-row">
                <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
                  <IconCheck />
                  Save Changes
                </button>
                <div className={`save-success${saveMessage ? ' visible' : ''}`} role="status">
                  <IconCheck />
                  Profile Updated Successfully
                </div>
              </div>
              {saveMessage ? (
                <span className="sr-only" role="status">
                  {saveMessage}
                </span>
              ) : null}
            </form>
          </div>
        </div>
      </section>

      <section className="db" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <div className="acct-card reveal">
            <h3 className="acct-card-title">
              <span className="act-ic">
                <IconLock />
              </span>
              Security
            </h3>
            {nativePasswordUser ? (
              <form onSubmit={(ev) => void onChangePassword(ev)}>
                <h4 className="pw-section-title">Change Password</h4>
                <div className="field-grid">
                  <div className="field">
                    <label htmlFor="pw-current">Current Password</label>
                    <input
                      type="password"
                      id="pw-current"
                      autoComplete="current-password"
                      placeholder="Enter current password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                    />
                  </div>
                  <div aria-hidden />
                  <div className="field">
                    <label htmlFor="pw-new">New Password</label>
                    <input
                      type="password"
                      id="pw-new"
                      autoComplete="new-password"
                      placeholder="Enter new password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="pw-confirm">Confirm New Password</label>
                    <input
                      type="password"
                      id="pw-confirm"
                      autoComplete="new-password"
                      placeholder="Confirm new password"
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                    />
                  </div>
                </div>
                <div className="pw-reqs">
                  {PW_ORDER.map((id) => (
                    <span key={id} className={`pw-req${pwChecks[id] ? ' met' : ''}`}>
                      <IconCheck />
                      {PW_LABELS[id]}
                    </span>
                  ))}
                </div>
                {passwordError ? (
                  <p className="save-error" role="alert">
                    {passwordError}
                  </p>
                ) : null}
                <div className="save-row" style={{ marginTop: 18 }}>
                  <button type="submit" className="btn btn-ghost btn-sm" disabled={changingPassword}>
                    Change Password
                  </button>
                  <div className={`save-success${passwordMessage ? ' visible' : ''}`} role="status">
                    <IconCheck />
                    Password Updated
                  </div>
                </div>
              </form>
            ) : (
              <p className="field-hint">You signed in with Google. Password changes are not available for this account.</p>
            )}
          </div>
        </div>
      </section>

      <section className="db" style={{ paddingTop: 0, paddingBottom: 80 }}>
        <div className="wrap">
          <div className="acct-card reveal">
            <h3 className="acct-card-title">
              <span className="act-ic">
                <IconBell />
              </span>
              Notification Preferences
            </h3>
            <p className="field-hint" style={{ marginBottom: 14, lineHeight: 1.55 }}>
              Course announcements, quiz results, certificates, Research Team updates, and product updates will be
              configurable here. Preferences are not editable in this release.
            </p>
            {NOTIFICATION_ROWS.map((row) => (
              <div className="toggle-row" key={row.key}>
                <div className="toggle-info">
                  <b>{row.title}</b>
                  <span>{row.detail}</span>
                </div>
                <button type="button" className="toggle-btn on" disabled aria-label={`Toggle ${row.title}`} />
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
