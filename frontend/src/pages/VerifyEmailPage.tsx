import { confirmSignUp, fetchAuthSession, signIn } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useRef, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'

import {
  ArrowIcon,
  BackIcon,
  ButtonSpinner,
  ChatIcon,
  ClockIcon,
  FaqList,
  LockIcon,
  MailIcon,
  PasswordToggle,
  ShieldIcon,
  TrustList,
  type FaqEntry,
} from '../components/auth/prototypeAuthParts'
import { usePageReveal } from '../components/auth/usePageReveal'
import { patchUsersMe } from '../lib/api/session'
import { isAuthConfigured } from '../lib/auth'
import {
  clearRegisterProfileDraft,
  readRegisterProfileDraft,
  REGISTER_PROFILE_DRAFT_KEY,
} from '../lib/register-profile-draft'
import { usePageTitle } from '../lib/page-title'
import './VerifyEmailPage.css'

const TRUST = [
  'Secure Email Confirmation',
  'One-Time Verification Code',
  'Profile Saved With Your Account',
  'Student Support Available',
] as const

const SECURITY = [
  {
    title: 'Secure Confirmation',
    body: 'Verification codes are sent only to the email address you entered when you created your account. Each code is unique to that registration.',
    icon: <LockIcon />,
  },
  {
    title: 'Email Code',
    body: 'Enter the code from your inbox to confirm you can receive mail at that address. Check the spam folder if it is not in your inbox.',
    icon: <MailIcon />,
  },
  {
    title: 'Account Protection',
    body: 'Confirming your email signs you in with the password you chose. Your name, country, profession, and agreements are saved to your profile.',
    icon: <ShieldIcon />,
  },
  {
    title: 'Student Support',
    body: 'If the code never arrives or the address was mistyped, contact the Research Spectrum support team and they can help you finish creating the account.',
    icon: <ChatIcon />,
  },
]

const STEPS = [
  ['Check Your Inbox', 'Open the verification email from Research Spectrum. Look in spam if it is not in the inbox.'],
  ['Enter The Code', 'Type the verification code into the form on this page.'],
  ['Confirm Your Password', 'Enter the password you chose at registration so we can sign you in.'],
  ['Continue Learning', 'Your profile is saved and you can enroll in courses from your account.'],
] as const

const FAQ: FaqEntry[] = [
  {
    question: 'How long does the verification code remain valid?',
    answer:
      'Use the code soon after it arrives. If it expires or you cannot find the email, register again with the same address to receive a new code. Codes are limited so an old message cannot confirm an account later.',
  },
  {
    question: "What if I don't receive the verification email?",
    answer:
      'Check your spam or junk folder first, and confirm the address you typed on the registration form. Delivery is usually within a few minutes. If it still does not arrive, contact Research Spectrum support.',
  },
  {
    question: 'Why do I need to enter my password again?',
    answer:
      'After the code is confirmed, Research Spectrum signs you in and saves the profile details from registration. The password never leaves this page except to complete that sign-in, and it is not stored in the browser.',
  },
  {
    question: 'What if I no longer have access to my email address?',
    answer: (
      <>
        Email confirmation needs the inbox for the address you registered. If you cannot open that inbox, contact
        Research Spectrum support through the{' '}
        <Link to="/contact" style={{ color: 'var(--blue)', fontWeight: 700 }}>
          Contact page
        </Link>
        .
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

export default function VerifyEmailPage() {
  usePageTitle('Verify email')
  const [params] = useSearchParams()
  const emailFromQuery = (params.get('email') ?? '').trim()
  const draft = readRegisterProfileDraft()
  const email = emailFromQuery || draft?.email || ''
  const authConfigured = isAuthConfigured()
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
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
    <div ref={rootRef} className="pg-verify-email" data-testid="student-page-verify-email">
      <section className="fp-hero">
        <div className="wrap">
          <div className="fp-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal">
                <span className="dot" />
                Email Verification
              </div>
              <h1 className="reveal" data-d="1">
                Verify Your{' '}
                <br />
                <span className="g">Email</span>
              </h1>
              <p className="sub reveal" data-d="2">
                Enter the verification code we sent and the password you chose so we can finish creating your Research
                Spectrum account.
              </p>
              <TrustList items={TRUST} />
              <p className="hero-alt reveal" data-d="4">
                Already verified? <Link to="/login">Sign In</Link>
              </p>
            </div>
            <div className="reveal" data-d="2">
              <div className="assist-card">
                <p className="ac-title">Verification Information</p>
                <div className="ac-row">
                  <span className="ac-label">
                    <MailIcon />
                    Method
                  </span>
                  <span className="ac-val">Email Code</span>
                </div>
                <div className="ac-row">
                  <span className="ac-label">
                    <ClockIcon />
                    Delivery
                  </span>
                  <span className="ac-val">Inbox And Spam</span>
                </div>
                <div className="ac-row">
                  <span className="ac-label">
                    <LockIcon />
                    Next Step
                  </span>
                  <span className="ac-val">Signed In Automatically</span>
                </div>
                <div className="ac-row">
                  <span className="ac-label">
                    <ShieldIcon />
                    Account Data
                  </span>
                  <span className="ac-val">Saved From Registration</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="reset-card-wrap">
        <div className="wrap">
          <div className="reset-card">
            <div className="rc-state active">
              <h2 className="rc-form-title">Confirm Your Email</h2>
              <p className="rc-form-sub">
                We sent a code to <strong>{email || 'your email'}</strong>. Enter it with your password to continue.
              </p>
              <form onSubmit={(ev) => void onSubmit(ev)}>
                <div className="field">
                  <label htmlFor="verifyCode">Verification Code</label>
                  <input
                    id="verifyCode"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    aria-required="true"
                    required
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="verifyPassword">Password</label>
                  <div className="pw-wrap">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="verifyPassword"
                      autoComplete="current-password"
                      aria-required="true"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <PasswordToggle shown={showPassword} onToggle={() => setShowPassword((v) => !v)} />
                  </div>
                </div>
                <p className="form-helper">
                  <ShieldIcon />
                  Your password is used only to sign you in after the code is confirmed.
                </p>
                {error ? (
                  <span className="err-msg" role="alert" style={{ display: 'block', marginBottom: 12 }}>
                    {error}
                  </span>
                ) : null}
                <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={submitting}>
                  <span>Verify and Continue</span>
                  <ButtonSpinner on={submitting} />
                  <ArrowIcon />
                </button>
              </form>
              <div className="rc-divider" />
              <Link to="/login" className="back-link">
                <BackIcon />
                Back to Sign In
              </Link>
              <span data-testid="register-draft-key" hidden>
                {REGISTER_PROFILE_DRAFT_KEY}
              </span>
            </div>
          </div>
        </div>
      </div>

      <section className="sec" style={{ padding: '72px 0' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 36 }} className="reveal">
            <p className="kicker">Account Security</p>
            <h2 style={sectionTitleStyle}>How Email Verification Works</h2>
            <p style={{ fontSize: 16, color: 'var(--body)', maxWidth: 580, margin: '14px auto 0', lineHeight: 1.65 }}>
              Research Spectrum confirms the email on your new account before signing you in.
            </p>
          </div>
          <div className="sec-grid reveal">
            {SECURITY.map((card) => (
              <div className="sec-card" key={card.title}>
                <div className="sc-ic">{card.icon}</div>
                <h3>{card.title}</h3>
                <p>{card.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)', padding: '72px 0 80px' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 48 }} className="reveal">
            <p className="kicker">Step by Step</p>
            <h2 style={sectionTitleStyle}>Email Verification Process</h2>
          </div>
          <div className="process-grid reveal">
            {STEPS.map(([title, body], index) => (
              <div className="process-step" key={title}>
                <div className="ps-node">{index + 1}</div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={{ padding: '72px 0 60px' }}>
        <div className="wrap">
          <div className="help-card reveal">
            <div className="hc-ic">
              <ChatIcon />
            </div>
            <div className="hc-body">
              <h3>Still Need Help?</h3>
              <p>
                If the verification email does not arrive, or you no longer have access to that address, our support
                team can help you finish creating your account.
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
