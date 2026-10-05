import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

import { usePageReveal } from '../components/auth/usePageReveal'
import { fetchMe, patchUsersMe } from '../lib/api/session'
import type { UserProfile } from '../lib/api/types'
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import { usePageTitle } from '../lib/page-title'
import { shouldSuppressInlineSessionSupersededMessage } from '../lib/session-superseded-inline'
import { RESEARCH_INTEREST_TOGGLES } from './settingsResearchInterests'
import './SettingsPage.css'

type PageState =
  | { status: 'loading' }
  | { status: 'superseded' }
  | { status: 'error'; message: string }
  | { status: 'ready'; profile: UserProfile }

type PrivacyPrefs = {
  showProfileToTeam: boolean
  allowTeamContact: boolean
  displayCertsPublicly: boolean
  anonymousAnalytics: boolean
}

const PRIVACY_DEFAULTS: PrivacyPrefs = {
  showProfileToTeam: true,
  allowTeamContact: true,
  displayCertsPublicly: false,
  anonymousAnalytics: true,
}

function platformVersionLabel(): string {
  const fromEnv = import.meta.env.VITE_APP_VERSION
  if (typeof fromEnv === 'string' && fromEnv.trim()) return fromEnv.trim()
  return 'v0.0.0'
}

function formatMonthYear(iso: string | undefined): string {
  if (!iso?.trim()) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(date)
}

function formatLastLogin(iso: string | undefined): string {
  if (!iso?.trim()) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  if (sameDay) return 'Today'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

function prefBool(profile: UserProfile, key: keyof UserProfile, fallback: boolean): boolean {
  const value = profile[key]
  return typeof value === 'boolean' ? value : fallback
}

function CardIcon({ children }: { children: ReactNode }) {
  return <span className="act-ic">{children}</span>
}

function SettingsToggle({
  label,
  title,
  detail,
  checked,
  disabled,
  onToggle,
}: {
  label: string
  title: string
  detail: string
  checked: boolean
  disabled?: boolean
  onToggle: () => void
}) {
  return (
    <div className="toggle-row">
      <div className="toggle-info">
        <b>{title}</b>
        <span>{detail}</span>
      </div>
      <button
        type="button"
        className={`toggle-btn${checked ? ' on' : ''}`}
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={onToggle}
      />
    </div>
  )
}

export default function SettingsPage() {
  usePageTitle('Settings')
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const [state, setState] = useState<PageState>({ status: 'loading' })
  const [privacy, setPrivacy] = useState<PrivacyPrefs>(PRIVACY_DEFAULTS)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [toastVisible, setToastVisible] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showToast = useCallback(() => {
    setToastVisible(true)
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToastVisible(false), 2000)
  }, [])

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const profile = await fetchMe()
        if (cancelled) return
        setState({ status: 'ready', profile })
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

  async function patchBuilt(
    patch: Parameters<typeof patchUsersMe>[0],
    applyLocal: (profile: UserProfile) => UserProfile,
  ) {
    if (state.status !== 'ready') return
    const previous = state.profile
    setSaveError(null)
    setSaving(true)
    setState({ status: 'ready', profile: applyLocal(previous) })
    try {
      const updated = await patchUsersMe(patch)
      setState({ status: 'ready', profile: updated })
      showToast()
    } catch (err) {
      setState({ status: 'ready', profile: previous })
      setSaveError(err instanceof Error ? err.message : catalogApiUserMessage(err))
    } finally {
      setSaving(false)
    }
  }

  function onBuiltBool(key: 'autoplayNext' | 'autoMarkComplete' | 'progressCelebrations') {
    if (state.status !== 'ready') return
    const current = prefBool(state.profile, key, true)
    const next = !current
    void patchBuilt({ [key]: next }, (profile) => ({ ...profile, [key]: next }))
  }

  function onResearchTag(tagKey: string) {
    if (state.status !== 'ready') return
    const tags = [...(state.profile.researchInterestTags ?? [])]
    const idx = tags.indexOf(tagKey)
    if (idx === -1) tags.push(tagKey)
    else tags.splice(idx, 1)
    void patchBuilt({ researchInterestTags: tags }, (profile) => ({
      ...profile,
      researchInterestTags: tags,
    }))
  }

  async function confirmReset() {
    if (state.status !== 'ready') return
    setResetOpen(false)
    setSaveError(null)
    setSaving(true)
    const previous = state.profile
    try {
      const updated = await patchUsersMe({ resetPreferences: true })
      setState({ status: 'ready', profile: updated })
      showToast()
    } catch (err) {
      setState({ status: 'ready', profile: previous })
      setSaveError(err instanceof Error ? err.message : catalogApiUserMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const profile = state.status === 'ready' ? state.profile : null
  const tags = profile?.researchInterestTags ?? []

  return (
    <div className="pg-settings" ref={rootRef} data-testid="student-page-settings">
      <section className="dash-hero">
        <div className="wrap">
          <div className="dash-hi reveal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Settings
          </div>
          <h1 className="reveal" data-d="1">
            <span className="g">Settings</span>
          </h1>
          <p className="sub reveal" data-d="2">
            Customize your Research Spectrum learning experience and platform preferences.
          </p>
        </div>
      </section>

      <section className="db">
        <div className="wrap">
          {state.status === 'loading' && <p className="reveal in">Loading settings…</p>}
          {state.status === 'superseded' && null}
          {state.status === 'error' && (
            <p className="settings-error reveal in" role="alert">
              {state.message}
            </p>
          )}
          {profile && (
            <>
              {saveError && (
                <p className="settings-error reveal in" role="alert">
                  {saveError}
                </p>
              )}
              <div className="settings-grid">
                <div className="acct-card reveal">
                  <h3 className="acct-card-title">
                    <CardIcon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                      </svg>
                    </CardIcon>
                    Learning Preferences
                  </h3>
                  <SettingsToggle
                    label="Autoplay Next Lecture"
                    title="Autoplay Next Lecture"
                    detail="Automatically begin the next lecture on completion."
                    checked={prefBool(profile, 'autoplayNext', true)}
                    disabled={saving}
                    onToggle={() => onBuiltBool('autoplayNext')}
                  />
                  <SettingsToggle
                    label="Auto-Mark Lecture Complete"
                    title="Auto-Mark Lecture Complete"
                    detail="Mark lectures done when you reach the end."
                    checked={prefBool(profile, 'autoMarkComplete', true)}
                    disabled={saving}
                    onToggle={() => onBuiltBool('autoMarkComplete')}
                  />
                </div>

                <div className="acct-card reveal" data-d="1">
                  <h3 className="acct-card-title">
                    <CardIcon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                      </svg>
                    </CardIcon>
                    In-Platform Notifications
                  </h3>
                  <SettingsToggle
                    label="Progress Celebrations"
                    title="Progress Celebrations"
                    detail="Show milestone animations when you complete modules."
                    checked={prefBool(profile, 'progressCelebrations', true)}
                    disabled={saving}
                    onToggle={() => onBuiltBool('progressCelebrations')}
                  />
                </div>

                <div className="acct-card reveal" data-d="1">
                  <h3 className="acct-card-title">
                    <CardIcon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      </svg>
                    </CardIcon>
                    Privacy
                  </h3>
                  <SettingsToggle
                    label="Show Profile to Research Team Members"
                    title="Show Profile to Research Team Members"
                    detail="Let Research Team collaborators see your public profile."
                    checked={privacy.showProfileToTeam}
                    onToggle={() =>
                      setPrivacy((p) => ({ ...p, showProfileToTeam: !p.showProfileToTeam }))
                    }
                  />
                  <SettingsToggle
                    label="Allow Research Team Contact"
                    title="Allow Research Team Contact"
                    detail="Let Research Spectrum contact you about team opportunities."
                    checked={privacy.allowTeamContact}
                    onToggle={() => setPrivacy((p) => ({ ...p, allowTeamContact: !p.allowTeamContact }))}
                  />
                  <SettingsToggle
                    label="Display Certificates Publicly"
                    title="Display Certificates Publicly"
                    detail="Make your certificate profile page publicly accessible."
                    checked={privacy.displayCertsPublicly}
                    onToggle={() =>
                      setPrivacy((p) => ({ ...p, displayCertsPublicly: !p.displayCertsPublicly }))
                    }
                  />
                  <SettingsToggle
                    label="Anonymous Learning Analytics"
                    title="Anonymous Learning Analytics"
                    detail="Contribute anonymized data to improve the platform."
                    checked={privacy.anonymousAnalytics}
                    onToggle={() =>
                      setPrivacy((p) => ({ ...p, anonymousAnalytics: !p.anonymousAnalytics }))
                    }
                  />
                </div>

                <div className="acct-card reveal">
                  <h3 className="acct-card-title">
                    <CardIcon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                      </svg>
                    </CardIcon>
                    Research Preferences
                  </h3>
                  {RESEARCH_INTEREST_TOGGLES.map((item) => (
                    <SettingsToggle
                      key={item.key}
                      label={item.label}
                      title={item.label}
                      detail={item.detail}
                      checked={tags.includes(item.key)}
                      disabled={saving}
                      onToggle={() => onResearchTag(item.key)}
                    />
                  ))}
                  <div className="research-callout">
                    <p className="rc-tag">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 11, height: 11 }} aria-hidden>
                        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                        <circle cx="9" cy="7" r="4" />
                        <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                      </svg>
                      Research Team Matching
                    </p>
                    <p>
                      When you apply for the Research Spectrum Research Team, these preferences are used to match you
                      with projects that align with your interests and expertise.
                    </p>
                  </div>
                </div>

                <div className="acct-card reveal" data-d="1">
                  <h3 className="acct-card-title">
                    <CardIcon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <rect x="2" y="3" width="20" height="14" rx="2" />
                        <line x1="8" y1="21" x2="16" y2="21" />
                        <line x1="12" y1="17" x2="12" y2="21" />
                      </svg>
                    </CardIcon>
                    Platform Information
                  </h3>
                  <div className="sys-row">
                    <span className="sys-lbl">Platform Version</span>
                    <span className="sys-badge">{platformVersionLabel()}</span>
                  </div>
                  <div className="sys-row">
                    <span className="sys-lbl">Member Since</span>
                    <span className="sys-val">{formatMonthYear(profile.createdAt)}</span>
                  </div>
                  <div className="sys-row">
                    <span className="sys-lbl">Last Login</span>
                    <span className="sys-val">{formatLastLogin(profile.lastLoginAt)}</span>
                  </div>
                </div>

                <div className="full reveal">
                  <div className="reset-card">
                    <div className="reset-info">
                      <h3>Reset Preferences</h3>
                      <p>
                        Restore learning preferences, progress celebrations, and research interests to their defaults.
                        Profile information and account data are not affected.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn-caution"
                      disabled={saving}
                      onClick={() => setResetOpen(true)}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }} aria-hidden>
                        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                        <path d="M3 3v5h5" />
                      </svg>
                      Restore Default Settings
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      <div className={`settings-toast${toastVisible ? ' show' : ''}`} aria-live="polite">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M20 6 9 17l-5-5" />
        </svg>
        Settings Saved
      </div>

      <div
        className={`modal-overlay${resetOpen ? ' open' : ''}`}
        role="presentation"
        onClick={(e) => {
          if (e.target === e.currentTarget) setResetOpen(false)
        }}
      >
        <div className="modal-box" role="dialog" aria-modal="true" aria-labelledby="settings-reset-title">
          <button type="button" className="modal-close-btn" aria-label="Close" onClick={() => setResetOpen(false)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
          <div className="modal-ic" style={{ background: '#fff5d6', color: '#a96b00' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
          </div>
          <h3 id="settings-reset-title">Restore Default Settings?</h3>
          <p>
            This will reset your saved learning preferences, progress celebrations, and research interests to their
            defaults. Your profile, certificates, and purchase history are not affected.
          </p>
          <div className="modal-actions">
            <button type="button" className="btn-caution" disabled={saving} onClick={() => void confirmReset()}>
              Yes, Restore Defaults
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setResetOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
