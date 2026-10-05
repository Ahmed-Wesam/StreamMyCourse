import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { SignIn } from '../components/auth/SignIn'
import { useAuthenticator } from '../lib/auth-ui'
import { isAuthConfigured } from '../lib/auth'
import { usePageTitle } from '../lib/page-title'
import './StudentLoginPage.css'

const TRUST = [
  'Access your purchased courses',
  'Continue exactly where you left off',
  'Track your certificate progress',
  'Complete quizzes and assignments',
  'Monitor Research Team eligibility',
] as const

function useReveal(rootRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const nodes = Array.from(root.querySelectorAll('.reveal'))
    if (typeof IntersectionObserver === 'undefined') {
      for (const el of nodes) el.classList.add('in')
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('in')
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' },
    )
    for (const el of nodes) observer.observe(el)
    return () => observer.disconnect()
  }, [rootRef])
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

function FaqItem({
  question,
  open,
  onToggle,
  children,
}: {
  question: string
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  return (
    <div className={open ? 'rt-faq-item open' : 'rt-faq-item'}>
      <button className="rt-faq-q" type="button" aria-expanded={open} onClick={onToggle}>
        <h3>{question}</h3>
        <div className="rt-faq-ic" aria-hidden="true">
          <PlusIcon />
        </div>
      </button>
      <div className="rt-faq-a" role="region">
        <p>{children}</p>
      </div>
    </div>
  )
}

export default function StudentLoginPage() {
  usePageTitle('Sign in')
  const authConfigured = isAuthConfigured()
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])
  const rootRef = useRef<HTMLDivElement>(null)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  useReveal(rootRef)

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Sign-in is not available: set Cognito <code className="rounded bg-rs-sky-2 px-1">VITE_*</code> variables for this
        SPA.
      </div>
    )
  }

  if (authStatus === 'authenticated') {
    return <Navigate to="/" replace />
  }

  function toggleFaq(index: number) {
    setOpenFaq((current) => (current === index ? null : index))
  }

  return (
    <div ref={rootRef} className="pg-login" data-testid="student-page-login">
      <section className="login-hero">
        <div className="wrap">
          <div className="login-hero-grid">
            <div className="hero-copy" data-testid="login-hero-column">
              <div className="eyebrow reveal">
                <span className="dot" />
                Research Spectrum
              </div>
              <h1 className="reveal" data-d="1">
                Welcome
                <br />
                <span className="g">Back</span>
              </h1>
              <p className="sub reveal" data-d="2">
                Sign in to access your courses, certificates, progress, and Research Team pathway.
              </p>
              <ul className="trust-list reveal" data-d="3">
                {TRUST.map((item) => (
                  <li key={item}>
                    <span className="ck">
                      <CheckIcon />
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
              <p className="hero-alt reveal" data-d="4">
                Don&apos;t have an account? <Link to="/register">Create one here</Link>
              </p>
            </div>

            <div className="reveal" data-d="2">
              <SignIn embedded />
            </div>
          </div>
        </div>
      </section>

      <section
        className="sec"
        id="faq"
        style={{
          background: 'var(--sky-2)',
          borderTop: '1px solid var(--line-2)',
          borderBottom: '1px solid var(--line-2)',
        }}
      >
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Account Help</p>
            <h2 className="title">Common Sign-In Questions</h2>
          </div>
          <div className="rt-faq-list reveal">
            <FaqItem
              question="I forgot my password — how do I reset it?"
              open={openFaq === 0}
              onToggle={() => toggleFaq(0)}
            >
              Click the <strong>Forgot password?</strong> link on the sign-in form. Enter your registered email address
              and we will send password reset instructions to that address. If you do not receive the email within a few
              minutes, check your spam or junk folder. Reset links expire after 24 hours for security.
            </FaqItem>
            <FaqItem
              question="Can I access my courses on multiple devices?"
              open={openFaq === 1}
              onToggle={() => toggleFaq(1)}
            >
              Yes. Your Research Spectrum account can be accessed from any device with a web browser — desktop, tablet,
              or mobile. Your progress is saved to your account, so you can begin a lesson on one device and continue on
              another without losing your place.
            </FaqItem>
            <FaqItem
              question="What should I do if I cannot access my registered email?"
              open={openFaq === 2}
              onToggle={() => toggleFaq(2)}
            >
              If you no longer have access to the email address registered to your account, please contact us through
              the{' '}
              <Link to="/contact" style={{ color: 'var(--blue)', fontWeight: 700 }}>
                Contact page
              </Link>
              . Include any details that can help verify your identity, such as your full name or previous purchase
              information, and our team will assist you.
            </FaqItem>
          </div>
        </div>
      </section>
    </div>
  )
}
