import { confirmResetPassword } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import {
  ArrowIcon,
  BackIcon,
  ButtonSpinner,
  ChatIcon,
  ClockIcon,
  FaqList,
  LockIcon,
  MailIcon,
  PasswordStrength,
  PasswordToggle,
  ShieldIcon,
  TrustList,
  type FaqEntry,
} from '../components/auth/prototypeAuthParts'
import { usePageReveal } from '../components/auth/usePageReveal'
import { isAuthConfigured } from '../lib/auth'
import { isPasswordPolicyMet } from '../lib/password-policy'
import { usePageTitle } from '../lib/page-title'
import './ResetPasswordPage.css'

const TRUST = [
  'Secure Password Update',
  'Protected Account Access',
  'Modern Security Standards',
  'Student Support Available',
] as const

const FAQ: FaqEntry[] = [
  {
    question: 'How strong should my new password be?',
    answer:
      'Your password should contain at least 8 characters including a combination of uppercase letters, lowercase letters, numbers, and special characters. The strength indicator on this page shows you in real time how strong your chosen password is. Aim for a "Strong" or "Excellent" rating. The stronger your password, the harder it is for unauthorized parties to access your account.',
  },
  {
    question: 'Can I reuse a previous password?',
    answer:
      'While the system may technically accept a previously used password, it is strongly recommended that you choose a new, unique password each time you reset. Reusing an old password, especially one that may have been compromised, reduces the security benefit of the reset process. Use a password manager to generate and store strong, unique passwords if needed.',
  },
  {
    question: 'What if my reset link expires before I use it?',
    answer: (
      <>
        Reset links are valid for 24 hours. If your link has expired, return to the{' '}
        <Link to="/forgot-password" style={{ color: 'var(--blue)', fontWeight: 700 }}>
          Forgot Password page
        </Link>{' '}
        and submit a new request. A fresh link will be sent to your registered email address. Each new request
        invalidates any previously sent links.
      </>
    ),
  },
  {
    question: 'How many times can I request a reset link?',
    answer:
      'You can request multiple reset links. Each new request generates a fresh link and invalidates any previous ones. If you requested a link and didn\'t receive it or it expired, simply return to the Forgot Password page and try again. If you continue experiencing issues, contact the Research Spectrum support team.',
  },
  {
    question: 'Why do password requirements exist?',
    answer:
      'Password requirements help ensure that your account is protected against common attacks such as brute-force and dictionary attacks. Simple passwords — such as dictionary words, common sequences, or short strings — can be guessed quickly. Combining uppercase letters, lowercase letters, numbers, and special characters makes your password exponentially harder to crack. Your Research Spectrum account holds course progress, certificates, and personal data worth protecting.',
  },
  {
    question: 'What should I do if I suspect unauthorized account access?',
    answer: (
      <>
        If you believe your account has been accessed without your authorization, change your password immediately using
        the reset process, then contact Research Spectrum support through the{' '}
        <Link to="/contact" style={{ color: 'var(--blue)', fontWeight: 700 }}>
          Contact page
        </Link>
        . Also change the password for the email account associated with your Research Spectrum profile, and check for
        any unexpected account activity in your settings.
      </>
    ),
  },
]

const sectionTitleStyle = {
  fontSize: 'clamp(26px,3.8vw,40px)',
  fontWeight: 800,
  letterSpacing: '-.025em',
  color: 'var(--ink)',
} as const

export default function ResetPasswordPage() {
  usePageTitle('Reset password')
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const emailDefault = (params.get('email') ?? '').trim()
  const authConfigured = isAuthConfigured()
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const [email, setEmail] = useState(emailDefault)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
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
  const confirmMismatch = confirmPassword.length > 0 && password !== confirmPassword
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
    <div ref={rootRef} className="pg-reset" data-testid="student-page-reset-password">
      <section className="rp-hero">
        <div className="wrap">
          <div className="rp-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal">
                <span className="dot" />
                Account Recovery
              </div>
              <h1 className="reveal" data-d="1">
                Create A <span className="g">New Password</span>
              </h1>
              <p className="sub reveal" data-d="2">
                Choose a strong password to secure your Research Spectrum account and continue your learning journey.
              </p>
              <TrustList items={TRUST} />
              <p className="hero-alt reveal" data-d="4">
                Remembered your password? <Link to="/login">Sign In</Link>
              </p>
            </div>
            <div className="reveal" data-d="2">
              <div className="sec-overview-card">
                <p className="soc-title">Account Security</p>
                <div className="soc-row">
                  <span className="soc-label">
                    <ClockIcon />
                    Status
                  </span>
                  <span className="soc-val">
                    <span className="soc-pill">Secure</span>
                  </span>
                </div>
                <div className="soc-row">
                  <span className="soc-label">
                    <LockIcon />
                    Password Protection
                  </span>
                  <span className="soc-val">Encrypted</span>
                </div>
                <div className="soc-row">
                  <span className="soc-label">
                    <ShieldIcon />
                    Account Recovery
                  </span>
                  <span className="soc-val">Verified link</span>
                </div>
                <div className="soc-row">
                  <span className="soc-label">
                    <MailIcon />
                    Email Verification
                  </span>
                  <span className="soc-val">Completed</span>
                </div>
                <div className="soc-row">
                  <span className="soc-label">
                    <ChatIcon />
                    Support
                  </span>
                  <span className="soc-val">1–2 business days</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="reset-card-wrap">
        <div className="wrap">
          <div className="reset-card" id="resetCard">
            <div className="rc-state active">
              <h2 className="rc-form-title">Create New Password</h2>
              <p className="rc-form-sub">Choose a strong, unique password for your Research Spectrum account.</p>
              <form onSubmit={(ev) => void onSubmit(ev)}>
                <div className="field">
                  <label htmlFor="resetEmail">Email Address</label>
                  <input
                    type="email"
                    id="resetEmail"
                    autoComplete="email"
                    aria-required="true"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="resetCode">Verification Code</label>
                  <input
                    id="resetCode"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    aria-required="true"
                    required
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </div>
                <div className="field" id="fNewPw">
                  <label htmlFor="newPw">New Password</label>
                  <div className="pw-wrap">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="newPw"
                      placeholder="Create a strong password"
                      autoComplete="new-password"
                      aria-required="true"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <PasswordToggle shown={showPassword} onToggle={() => setShowPassword((v) => !v)} />
                  </div>
                  <span className="err-msg" role="alert" />
                  <PasswordStrength password={password} variant="reset" />
                </div>
                <div className={confirmMismatch ? 'field has-err' : 'field'} id="fConfirmPw">
                  <label htmlFor="confirmPw">Confirm New Password</label>
                  <div className="pw-wrap">
                    <input
                      type={showConfirm ? 'text' : 'password'}
                      id="confirmPw"
                      placeholder="Repeat your new password"
                      autoComplete="new-password"
                      aria-required="true"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                    <PasswordToggle shown={showConfirm} onToggle={() => setShowConfirm((v) => !v)} />
                  </div>
                  <span className="err-msg" role="alert">
                    {confirmMismatch ? 'Passwords do not match.' : ''}
                  </span>
                </div>
                {error ? (
                  <span className="err-msg" role="alert" style={{ display: 'block', marginBottom: 12 }}>
                    {error}
                  </span>
                ) : null}
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
                  disabled={!canSubmit}
                >
                  <span>Update Password</span>
                  <ButtonSpinner on={submitting} />
                  <ArrowIcon />
                </button>
              </form>
              <div className="rc-divider" />
              <Link to="/login" className="back-link">
                <BackIcon />
                Back to Sign In
              </Link>
            </div>
          </div>

          <div className="info-card reveal" style={{ marginTop: 20 }}>
            <div className="ic-icon">
              <LockIcon />
            </div>
            <div className="ic-body">
              <h3>Why Password Strength Matters</h3>
              <p>
                A strong password protects your course access, certificates, and account progress. Research Spectrum
                certificates and assignment records are linked to your account — use a unique, strong password to keep
                them secure. Never share your password with anyone.
              </p>
            </div>
          </div>
        </div>
      </div>

      <section style={{ padding: '72px 0 60px' }}>
        <div className="wrap">
          <div className="help-card reveal">
            <div className="hc-ic">
              <ChatIcon />
            </div>
            <div className="hc-body">
              <h3>Need Additional Assistance?</h3>
              <p>
                If you&apos;re unable to reset your password, your link has expired, or you can no longer access your
                registered email, our support team is available to help verify your identity and restore account access.
              </p>
            </div>
            <div className="hc-actions">
              <Link to="/contact" className="btn btn-primary btn-sm">
                Contact Support <ArrowIcon />
              </Link>
              <Link to="/login" className="btn btn-ghost btn-sm">
                Back To Sign In
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section style={{ padding: '0 0 80px', borderTop: '1px solid var(--line-2)' }}>
        <div className="wrap" style={{ paddingTop: 72 }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }} className="reveal">
            <p className="kicker">Questions</p>
            <h2 style={sectionTitleStyle}>Common Questions</h2>
          </div>
          <FaqList items={FAQ} />
        </div>
      </section>
    </div>
  )
}
