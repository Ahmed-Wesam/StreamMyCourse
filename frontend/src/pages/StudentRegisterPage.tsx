import { signUp } from 'aws-amplify/auth'
import type { FormEvent } from 'react'
import { useMemo, useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import {
  ArrowIcon,
  ButtonSpinner,
  FaqList,
  PasswordStrength,
  PasswordToggle,
  TrustList,
  type FaqEntry,
} from '../components/auth/prototypeAuthParts'
import { usePageReveal } from '../components/auth/usePageReveal'
import { useAuthenticator } from '../lib/auth-ui'
import { isAuthConfigured } from '../lib/auth'
import { isPasswordPolicyMet } from '../lib/password-policy'
import { COUNTRIES, PROFESSIONS } from '../lib/profile-options'
import { saveRegisterProfileDraft } from '../lib/register-profile-draft'
import { usePageTitle } from '../lib/page-title'
import './StudentRegisterPage.css'

const TRUST = [
  'Structured Research Training',
  'Four Comprehensive Courses',
  'Competency-Based Certificates',
  'Research Team Pathway',
  'Lifetime Course Access',
] as const

const PATHWAY = [
  ['Create Account', 'Register in seconds — no payment required to create an account.'],
  ['Enroll In Courses', 'Choose individual courses or enroll in the full four-course pathway.'],
  ['Complete Modules', 'Work through expert-led video lectures, readings, and exercises at your own pace.'],
  ['Pass Module Quizzes', 'Demonstrate mastery of each module with knowledge checks. Unlimited attempts — mastery learning, not time pressure.'],
  ['Submit Final Assignment', 'Apply course skills to a real dataset or research scenario. Receive detailed evaluator feedback.'],
  ['Earn Your Certificate', "Verified Research Spectrum certificates are issued automatically upon passing each course's final assessment."],
  ['Apply To The Research Team', 'Hold all four certificates and become eligible to apply. Contribute to published research and build your academic profile.'],
] as const

const FAQ: FaqEntry[] = [
  {
    question: 'Is registration free?',
    answer:
      'Yes. Creating a Research Spectrum account is completely free. Once registered, you can explore the platform, browse course content, and enroll in individual courses. Course enrollment requires a one-time purchase per course, or you may purchase the full four-course bundle.',
  },
  {
    question: 'Do I need prior research experience?',
    answer:
      'No prior research experience is required. Research Spectrum is designed to take healthcare professionals from no research background to independently capable researchers. The curriculum is structured progressively — each course builds on the previous one, beginning with the foundational concepts every researcher needs.',
  },
  {
    question: 'Can I enroll in individual courses?',
    answer:
      'Yes. Each of the four courses — Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis — can be purchased individually. A bundled option is also available for students who want access to all four courses at once, which is recommended for the Research Team pathway.',
  },
  {
    question: 'Will I receive certificates?',
    answer:
      "Yes. Each completed course awards a verifiable Research Spectrum certificate, which is accessible from your dashboard and can be verified online using a unique code. Completing all four certificates makes you eligible to apply for the Research Team. Certificates are issued only after successfully passing all required module quizzes and the final assignment for each course.",
  },
  {
    question: 'Can I join the Research Team immediately after registering?',
    answer:
      'No. Eligibility to apply for the Research Team requires completing all four Research Spectrum courses and earning each course\'s certificate. The four-course curriculum ensures that Research Team members have the skills needed to contribute meaningfully to published research projects. Registering is the first step on that pathway.',
  },
  {
    question: 'How is Research Spectrum different from other platforms?',
    answer:
      'Research Spectrum is purpose-built for healthcare professionals who want to publish research — not a general-purpose learning platform. The curriculum is designed by researchers for researchers, with a specific focus on the practical skills required for independent research and publication. Unlike platforms that award certificates simply for completion, Research Spectrum certificates reflect demonstrated competency, assessed through graded assignments and reviewed by subject-matter evaluators.',
  },
]

export default function StudentRegisterPage() {
  usePageTitle('Create account')
  const navigate = useNavigate()
  const authConfigured = isAuthConfigured()
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const [givenName, setGivenName] = useState('')
  const [familyName, setFamilyName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
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
  const confirmMismatch = confirmPassword.length > 0 && password !== confirmPassword

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
    <div ref={rootRef} className="pg-register" data-testid="student-page-register">
      <section className="reg-hero">
        <div className="wrap">
          <div className="reg-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal">
                <span className="dot" />
                Research Spectrum
              </div>
              <h1 className="reveal" data-d="1">
                Create Your{' '}
                <br />
                <span className="g">Research Spectrum</span>{' '}
                <br />
                Account
              </h1>
              <p className="sub reveal" data-d="2">
                Join a structured research education platform designed to help healthcare professionals develop practical
                research skills from study design through publication.
              </p>
              <TrustList items={TRUST} />
              <p className="hero-alt reveal" data-d="4">
                Already have an account? <Link to="/login">Sign In</Link>
              </p>
            </div>

            <div className="reveal" data-d="2" id="regCard">
              <div className="auth-card">
                <h2 className="auth-title">Create Account</h2>
                <p className="auth-sub">Join Research Spectrum and start building your research skills.</p>

                <form id="regForm" noValidate autoComplete="on" onSubmit={(ev) => void onSubmit(ev)}>
                  <div className="field-grid">
                    <div className="field" id="fFirstName">
                      <label htmlFor="firstName">First Name</label>
                      <input
                        type="text"
                        id="firstName"
                        name="firstName"
                        placeholder="First name"
                        autoComplete="given-name"
                        aria-required="true"
                        required
                        value={givenName}
                        onChange={(e) => setGivenName(e.target.value)}
                      />
                      <span className="err-msg" role="alert" />
                    </div>
                    <div className="field" id="fLastName">
                      <label htmlFor="lastName">Last Name</label>
                      <input
                        type="text"
                        id="lastName"
                        name="lastName"
                        placeholder="Last name"
                        autoComplete="family-name"
                        aria-required="true"
                        required
                        value={familyName}
                        onChange={(e) => setFamilyName(e.target.value)}
                      />
                      <span className="err-msg" role="alert" />
                    </div>
                  </div>

                  <div className="field" id="fEmail">
                    <label htmlFor="regEmail">Email Address</label>
                    <input
                      type="email"
                      id="regEmail"
                      name="email"
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

                  <div className="field" id="fPassword">
                    <label htmlFor="regPassword">Password</label>
                    <div className="pw-wrap">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        id="regPassword"
                        name="password"
                        placeholder="Create a password"
                        autoComplete="new-password"
                        aria-required="true"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                      />
                      <PasswordToggle shown={showPassword} onToggle={() => setShowPassword((v) => !v)} />
                    </div>
                    <span className="err-msg" role="alert" />
                    <PasswordStrength password={password} variant="register" />
                  </div>

                  <div className={confirmMismatch ? 'field has-err' : 'field'} id="fConfirm">
                    <label htmlFor="regConfirm">Confirm Password</label>
                    <div className="pw-wrap">
                      <input
                        type={showConfirm ? 'text' : 'password'}
                        id="regConfirm"
                        name="confirm"
                        placeholder="Repeat your password"
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

                  <div className="field-grid">
                    <div className="field" id="fCountry">
                      <label htmlFor="regCountry">Country</label>
                      <select
                        id="regCountry"
                        name="country"
                        aria-required="true"
                        required
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                      >
                        <option value="">Select country…</option>
                        {COUNTRIES.map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </select>
                      <span className="err-msg" role="alert" />
                    </div>
                    <div className="field" id="fProfession">
                      <label htmlFor="regProfession">Profession</label>
                      <select
                        id="regProfession"
                        name="profession"
                        aria-required="true"
                        required
                        value={profession}
                        onChange={(e) => setProfession(e.target.value)}
                      >
                        <option value="">Select profession…</option>
                        {PROFESSIONS.map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </select>
                      <span className="err-msg" role="alert" />
                    </div>
                  </div>

                  <div className="field">
                    <label htmlFor="regInstitution">
                      Institution <span className="field-opt">(optional)</span>
                    </label>
                    <input
                      type="text"
                      id="regInstitution"
                      name="institution"
                      placeholder="e.g. King Hussein Medical Centre"
                      autoComplete="organization"
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                    />
                  </div>

                  <div className="field">
                    <label htmlFor="regInterests">
                      Research Interests <span className="field-opt">(optional)</span>
                    </label>
                    <textarea
                      id="regInterests"
                      name="interests"
                      placeholder="e.g. cardiology, systematic reviews, clinical trials…"
                      rows={2}
                      value={researchInterests}
                      onChange={(e) => setResearchInterests(e.target.value)}
                    />
                  </div>

                  <div className="auth-divider" />
                  <div className="cb-row">
                    <input
                      type="checkbox"
                      id="cbTerms"
                      name="terms"
                      aria-required="true"
                      checked={termsAccepted}
                      onChange={(e) => setTermsAccepted(e.target.checked)}
                    />
                    <label htmlFor="cbTerms">
                      I agree to the{' '}
                      <Link to="/terms" target="_blank" rel="noopener noreferrer">
                        Terms &amp; Conditions
                      </Link>
                    </label>
                  </div>
                  <span className="cb-err" role="alert">
                    You must agree to the Terms &amp; Conditions to continue.
                  </span>
                  <div className="cb-row">
                    <input
                      type="checkbox"
                      id="cbPrivacy"
                      name="privacy"
                      aria-required="true"
                      checked={privacyAccepted}
                      onChange={(e) => setPrivacyAccepted(e.target.checked)}
                    />
                    <label htmlFor="cbPrivacy">
                      I agree to the{' '}
                      <Link to="/privacy" target="_blank" rel="noopener noreferrer">
                        Privacy Policy
                      </Link>
                    </label>
                  </div>
                  <span className="cb-err" role="alert">
                    You must agree to the Privacy Policy to continue.
                  </span>

                  <div className={error ? 'form-err visible' : 'form-err'} role="alert" aria-live="assertive">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    <span>{error}</span>
                  </div>

                  <button
                    type="submit"
                    className="btn btn-primary"
                    id="submitBtn"
                    data-testid="register-submit"
                    style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
                    disabled={!canSubmit}
                  >
                    <span>Create Account</span>
                    <ButtonSpinner on={submitting} />
                    <ArrowIcon />
                  </button>

                  <div className="auth-divider" />
                  <p className="auth-alt">
                    Already have an account? <Link to="/login">Sign In</Link>
                  </p>
                </form>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        className="sec"
        style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}
      >
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Your Journey</p>
            <h2 className="title">What Happens After You Register</h2>
            <p className="lead">A clear, achievable pathway from your first course to your first publication.</p>
          </div>
          <div className="pathway-wrap reveal">
            <div className="pathway-line" />
            {PATHWAY.map(([title, body], index) => (
              <div className="pathway-step" key={title}>
                <div className="path-node">{index + 1}</div>
                <div className="path-info">
                  <h4>{title}</h4>
                  <p>{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sec" id="faq">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Questions</p>
            <h2 className="title">Frequently Asked Questions</h2>
          </div>
          <FaqList items={FAQ} />
        </div>
      </section>
    </div>
  )
}
