import { useState, type ReactNode } from 'react'

import { passwordChecks } from '../../lib/password-policy'

function Icon({ children, strokeWidth = 2 }: { children: ReactNode; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  )
}

function CheckIcon() {
  return (
    <Icon strokeWidth={2.8}>
      <path d="M20 6 9 17l-5-5" />
    </Icon>
  )
}

export function ArrowIcon() {
  return (
    <Icon strokeWidth={2.5}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  )
}

export function BackIcon() {
  return (
    <Icon strokeWidth={2.5}>
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </Icon>
  )
}

function PlusIcon() {
  return (
    <Icon strokeWidth={2.5}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Icon>
  )
}

export function LockIcon() {
  return (
    <Icon>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </Icon>
  )
}

export function MailIcon() {
  return (
    <Icon>
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </Icon>
  )
}

export function ClockIcon() {
  return (
    <Icon>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </Icon>
  )
}

export function ShieldIcon() {
  return (
    <Icon>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </Icon>
  )
}

export function ChatIcon() {
  return (
    <Icon>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </Icon>
  )
}

export function TrustList({ items }: { items: readonly string[] }) {
  return (
    <ul className="trust-list reveal" data-d="3">
      {items.map((item) => (
        <li key={item}>
          <span className="ck">
            <CheckIcon />
          </span>
          {item}
        </li>
      ))}
    </ul>
  )
}

export type FaqEntry = { question: string; answer: ReactNode }

export function FaqList({ items }: { items: readonly FaqEntry[] }) {
  const [open, setOpen] = useState<number | null>(null)
  return (
    <div className="rt-faq-list reveal">
      {items.map((item, index) => {
        const isOpen = open === index
        return (
          <div className={isOpen ? 'rt-faq-item open' : 'rt-faq-item'} key={item.question}>
            <button
              className="rt-faq-q"
              type="button"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : index)}
            >
              <h3>{item.question}</h3>
              <div className="rt-faq-ic" aria-hidden="true">
                <PlusIcon />
              </div>
            </button>
            <div className="rt-faq-a" role="region">
              <p>{item.answer}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function PasswordToggle({ shown, onToggle }: { shown: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      className="pw-toggle"
      aria-label={shown ? 'Hide password' : 'Show password'}
      aria-pressed={shown}
      onClick={onToggle}
    >
      <svg style={{ display: shown ? 'none' : undefined }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
      <svg style={{ display: shown ? undefined : 'none' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </svg>
    </button>
  )
}

export function ButtonSpinner({ on }: { on: boolean }) {
  return <div className={on ? 'btn-spinner v' : 'btn-spinner'} aria-hidden="true" />
}

const RESET_STRENGTH = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Excellent'] as const

export function PasswordStrength({
  password,
  variant,
}: {
  password: string
  variant: 'register' | 'reset'
}) {
  const checks = passwordChecks(password)
  const items = [
    { met: checks.length, label: '8+ characters' },
    { met: checks.upper, label: 'Uppercase letter' },
    { met: checks.lower, label: 'Lowercase letter' },
    { met: checks.number, label: 'Number' },
    { met: /[^A-Za-z0-9]/.test(password), label: 'Special character' },
  ]
  const score = items.filter((item) => item.met).length
  const level = score <= 1 ? 'weak' : score <= 3 ? 'moderate' : 'strong'
  const fillClass = variant === 'register' ? `pw-strength-fill psf-${level}` : `pw-strength-fill psf-${score}`
  const labelClass = variant === 'register' ? `pw-strength-lbl psl-${level}` : `pw-strength-lbl psl-${score}`
  const label = variant === 'register' ? level.charAt(0).toUpperCase() + level.slice(1) : (RESET_STRENGTH[score] ?? '')

  return (
    <div className="pw-strength" style={{ display: password ? undefined : 'none' }}>
      <div className="pw-strength-bar">
        <div className={fillClass} />
      </div>
      <span className={labelClass}>{label}</span>
      <ul className="pw-checklist" data-testid="password-checklist">
        {items.map((item) => (
          <li key={item.label} className={item.met ? 'pw-check-item met' : 'pw-check-item'}>
            <div className="pw-ci">
              <CheckIcon />
            </div>
            {item.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
