import { resetPassword } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  ArrowIcon,
  BackIcon,
  ButtonSpinner,
  ChatIcon,
  ClockIcon,
  FaqList,
  LockIcon,
  MailIcon,
  ShieldIcon,
  TrustList,
  type FaqEntry,
} from '../components/auth/prototypeAuthParts'
import { usePageReveal } from '../components/auth/usePageReveal'
import { isAuthConfigured } from '../lib/auth'
import { usePageTitle } from '../lib/page-title'
import './ForgotPasswordPage.css'

const GENERIC_SUCCESS =
  'If an account exists for that email, we sent password reset instructions. Check your inbox and spam folder.'

const TRUST = [
  'Secure Account Recovery',
  'Fast Reset Process',
  'Protecting Your Account',
  'Student Support Available',
] as const

const SECURITY = [
  {
    title: 'Secure Recovery',
    body: 'Password reset links are cryptographically secured and sent only to your registered email address. Each link is unique and valid for 24 hours.',
    icon: <LockIcon />,
  },
  {
    title: 'Email Verification',
    body: 'Only the owner of the registered email address can reset the password. Research Spectrum never shares or transfers account credentials.',
    icon: <MailIcon />,
  },
  {
    title: 'Account Protection',
    body: 'Requesting a reset does not affect your course access, certificates, or progress. Your account data remains intact throughout the recovery process.',
    icon: <ShieldIcon />,
  },
  {
    title: 'Student Support',
    body: 'If you no longer have access to your registered email address, the Research Spectrum support team can help verify your identity and restore access.',
    icon: <ChatIcon />,
  },
] as const

const STEPS = [
  ['Request Reset', 'Enter your registered email address and click Send Reset Instructions.'],
  ['Check Email', 'Open the reset email from Research Spectrum. Check your inbox and spam folder if needed.'],
  ['Create New Password', 'Click the link in the email and choose a new secure password for your account.'],
  ['Return to Learning', 'Sign in with your new password and continue your research education journey.'],
] as const

const FAQ: FaqEntry[] = [
  {
    question: 'How long does the reset link remain valid?',
    answer:
      'Password reset links are valid for 24 hours from the time the email is sent. If you do not use the link within that time, it will expire and you will need to request a new reset email. This time limit is in place for security — it ensures that old links cannot be used if an email is later accessed by an unauthorized party.',
  },
  {
    question: "What if I don't receive the reset email?",
    answer:
      "First, check your spam or junk folder — reset emails occasionally end up there. Make sure the email address you entered matches the one registered with your account. Emails are typically delivered within a few minutes. If you still don't receive the email after a few minutes, use the Resend Email option on the confirmation page. If the issue persists, contact Research Spectrum support.",
  },
  {
    question: 'What if I accidentally entered the wrong email address?',
    answer:
      'Simply submit another password reset request using the correct email address. Only the most recent valid reset link should be used.',
  },
  {
    question: 'Can I request multiple reset emails?',
    answer:
      'Yes. You can request multiple reset emails. Each new request generates a new link and the previous link becomes invalid. If you requested a reset and didn\'t receive the email, or the link expired before you used it, simply return to this page and submit a new request.',
  },
  {
    question: 'What if I no longer have access to my email address?',
    answer: (
      <>
        If you no longer have access to the email address associated with your account, standard email-based password
        reset will not work. Contact Research Spectrum support through the{' '}
        <Link to="/contact" style={{ color: 'var(--blue)', fontWeight: 700 }}>
          Contact page
        </Link>
        . The support team can verify your identity through other means and help you update your email address or restore
        access to your account.
      </>
    ),
  },
  {
    question: 'How long does account recovery take?',
    answer:
      'Email-based password reset is typically completed within minutes — as soon as you receive the email and create your new password. If you require manual support from the team (for example, because you no longer have email access), the support team responds within 1–2 business days.',
  },
  {
    question: 'Can support reset my password for me?',
    answer:
      'Research Spectrum support will not set a specific password on your behalf — passwords must be set by you to ensure your account security. However, the support team can initiate a password reset process, verify your identity, and assist you in regaining access through secure means if standard email recovery is unavailable.',
  },
]

const sectionTitleStyle = {
  fontSize: 'clamp(26px,3.8vw,40px)',
  fontWeight: 800,
  letterSpacing: '-.025em',
  color: 'var(--ink)',
} as const

export default function ForgotPasswordPage() {
  usePageTitle('Forgot password')
  const authConfigured = isAuthConfigured()
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)
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

  async function sendReset(e?: FormEvent) {
    e?.preventDefault()
    if (!email.trim() || submitting) return
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
    <div ref={rootRef} className="pg-forgot" data-testid="student-page-forgot-password">
      <section className="fp-hero">
        <div className="wrap">
          <div className="fp-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal">
                <span className="dot" />
                Account Recovery
              </div>
              <h1 className="reveal" data-d="1">
                Forgot Your{' '}
                <br />
                <span className="g">Password?</span>
              </h1>
              <p className="sub reveal" data-d="2">
                Enter the email address associated with your account and we&apos;ll send secure password reset
                instructions.
              </p>
              <TrustList items={TRUST} />
              <p className="hero-alt reveal" data-d="4">
                Remembered your password? <Link to="/login">Sign In</Link>
              </p>
            </div>
            <div className="reveal" data-d="2">
              <div className="assist-card">
                <p className="ac-title">Account Recovery Information</p>
                <div className="ac-row">
                  <span className="ac-label">
                    <LockIcon />
                    Reset Method
                  </span>
                  <span className="ac-val">Email Verification</span>
                </div>
                <div className="ac-row">
                  <span className="ac-label">
                    <ClockIcon />
                    Link Expiry
                  </span>
                  <span className="ac-val">24 Hours</span>
                </div>
                <div className="ac-row">
                  <span className="ac-label">
                    <ChatIcon />
                    Support Response
                  </span>
                  <span className="ac-val">1–2 Business Days</span>
                </div>
                <div className="ac-row">
                  <span className="ac-label">
                    <ShieldIcon />
                    Account Data
                  </span>
                  <span className="ac-val">Preserved During Recovery</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="reset-card-wrap">
        <div className="wrap">
          <div className="reset-card" id="resetCard">
            {sent ? (
              <div className="rc-state active" role="status">
                <div className="rc-success-ic">
                  <MailIcon />
                </div>
                <div className="rc-success-title">Check Your Email</div>
                <p className="rc-success-body">{GENERIC_SUCCESS}</p>
                <div style={{ textAlign: 'center', marginBottom: 22 }}>
                  <div className="rc-email-pill" style={{ display: 'inline-flex' }}>
                    <MailIcon />
                    <span>{email.trim()}</span>
                  </div>
                </div>
                <div className="rc-state-actions">
                  <Link to="/login" className="btn btn-primary">
                    Back To Sign In <ArrowIcon />
                  </Link>
                  <button type="button" className="btn btn-ghost" onClick={() => void sendReset()}>
                    Resend Email
                  </button>
                  <Link to="/contact" className="btn btn-ghost">
                    Contact Support
                  </Link>
                  <Link to="/reset-password" className="btn btn-ghost">
                    Enter Reset Link
                  </Link>
                </div>
              </div>
            ) : (
              <div className="rc-state active">
                <h2 className="rc-form-title">Reset Your Password</h2>
                <p className="rc-form-sub">
                  Enter your account email address and we&apos;ll send you instructions to create a new password.
                </p>
                <form onSubmit={(ev) => void sendReset(ev)}>
                  <div className="field" id="fResetEmail">
                    <label htmlFor="resetEmail">Email Address</label>
                    <input
                      type="email"
                      id="resetEmail"
                      placeholder="your@email.com"
                      autoComplete="email"
                      inputMode="email"
                      aria-required="true"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                    <span className="err-msg" role="alert" />
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: -8, marginBottom: 16, lineHeight: 1.5 }}>
                    Your courses, certificates, and learning progress will remain unchanged.
                  </p>
                  <p className="form-helper">
                    <ShieldIcon />
                    We&apos;ll send reset instructions only to the email registered with your account.
                  </p>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={submitting}>
                    <span>Send Reset Instructions</span>
                    <ButtonSpinner on={submitting} />
                    <ArrowIcon />
                  </button>
                </form>
                <div className="rc-divider" />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
                  <Link to="/login" className="back-link">
                    <BackIcon />
                    Back to Sign In
                  </Link>
                  <Link to="/register" style={{ fontSize: 14, color: 'var(--blue)', fontWeight: 700 }}>
                    Create Account
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <section className="sec" style={{ padding: '72px 0' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 36 }} className="reveal">
            <p className="kicker">Account Security</p>
            <h2 style={sectionTitleStyle}>How Account Recovery Works</h2>
            <p style={{ fontSize: 16, color: 'var(--body)', maxWidth: 580, margin: '14px auto 0', lineHeight: 1.65 }}>
              Research Spectrum uses email-based account recovery to keep your account secure and accessible.
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
            <h2 style={sectionTitleStyle}>Password Reset Process</h2>
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
                If you&apos;re unable to access your account or no longer have access to your registered email address, our
                support team can help verify your identity and restore access to your account and course progress.
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
