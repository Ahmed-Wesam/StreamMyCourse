import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  getPublicCertificate,
  type PublicCertificateResult,
} from '../lib/api/public-certificates'
import { usePageTitle } from '../lib/page-title'
import './VerifyCertificatePage.css'

const DEFAULT_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

const COMPETENCIES_BY_COURSE: Record<string, readonly string[]> = {
  'Research Methodology': [
    'Study Design Selection',
    'Formulate Research Questions',
    'Develop Study Protocols',
    'Identify Variables & Outcomes',
    'Apply Research Ethics Principles',
  ],
  'Statistics & SPSS': [
    'Perform Descriptive Statistical Analysis',
    'Conduct Hypothesis Testing',
    'Interpret SPSS Output',
    'Select Appropriate Statistical Tests',
    'Build and Interpret Regression Models',
  ],
  'Scientific Writing': [
    'Structure Scientific Manuscripts',
    'Write Methods and Results Sections',
    'Report Statistical Findings Correctly',
    'Apply Journal Submission Standards',
    'Critically Revise Scientific Writing',
  ],
  'Systematic Reviews & Meta-Analysis': [
    'Conduct Structured Literature Searches',
    'Perform Study Screening',
    'Extract Research Data',
    'Apply PRISMA Methodology',
    'Interpret Evidence Synthesis Findings',
  ],
}

const JOURNEY = [
  ['Course Enrollment', 'Enrolled in course'],
  ['Modules Completed', 'All modules finished'],
  ['Quizzes Passed', 'Module quizzes mastered'],
  ['Assignment Passed', 'Final competency assessment'],
  ['Certificate Awarded', 'Competency confirmed'],
] as const

const WHY = [
  {
    title: 'Authenticity',
    body: 'Verify that a certificate is genuine and unaltered.',
    icon: 'shield' as const,
  },
  {
    title: 'Competency Validation',
    body: 'Certificates represent demonstrated, assessed skills.',
    icon: 'check' as const,
  },
  {
    title: 'Professional Credibility',
    body: 'Supports academic and professional applications.',
    icon: 'user' as const,
  },
  {
    title: 'Independent Verification',
    body: 'Verification is publicly accessible without login.',
    icon: 'search' as const,
  },
]

const FAQ = [
  {
    question: 'What information is required to verify a certificate?',
    answer:
      'Only the credential ID is required. Each Research Spectrum certificate contains a unique credential ID (for example, RS-RM-2026-A1B7F3) which can be found on the certificate document. Enter this ID in the search field above to verify the certificate instantly.',
  },
  {
    question: 'Can a certificate be revoked?',
    answer:
      'In rare circumstances, Research Spectrum may revoke a certificate if it was issued in error, if assessment integrity concerns are identified, or if the credential holder requests revocation. A revoked certificate will appear as revoked through this verification system, with the reason provided where applicable. The verification status always reflects the current state of the certificate.',
  },
  {
    question: 'What does verified status mean?',
    answer:
      'A verified status confirms that the certificate is authentic, was issued by Research Spectrum, is currently valid, and has not been revoked. It also confirms the named certificate holder successfully completed all required assessments — including module quizzes and a graded final assignment — for the specified course.',
  },
  {
    question: 'Do Research Spectrum certificates expire?',
    answer:
      'Research Spectrum certificates do not carry an expiration date. They reflect the successful completion of course requirements at the time of issue and remain valid indefinitely. The knowledge and skills demonstrated by the assessments do not expire, though learners are encouraged to stay current with developments in their field.',
  },
  {
    question: 'Can employers and institutions verify certificates?',
    answer:
      'Yes. This verification page is publicly accessible and requires no login. Employers, residency programs, research supervisors, universities, and any other party can independently verify the authenticity and current status of a Research Spectrum certificate using only the credential ID printed on the certificate document.',
  },
  {
    question: 'What if a certificate cannot be found?',
    answer:
      'If a certificate ID cannot be found in the system, it may indicate that the ID was entered incorrectly, the certificate was not issued by Research Spectrum, or there is a data issue on our end. Please double-check the credential ID on the original certificate document. If you believe the certificate is genuine and the issue persists, contact Research Spectrum support using the form below.',
  },
] as const

type UiStatus = 'verified' | 'not_found' | 'revoked' | 'expired' | 'pending'

type VerifiedCert = {
  name: string
  course: string
  credentialId: string
  issueDate: string
  instructor: string
  competencies: readonly string[]
}

type ReadyView = {
  status: UiStatus
  queryId: string
  checkedAt: string
  cert: VerifiedCert | null
  revokedReason?: string
}

type Phase =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; view: ReadyView }

const STATUS_COPY: Record<UiStatus, { pillClass: string; iconClass: string; cardClass: string; pillLabel: string; title: string; description: string }> = {
  verified: {
    pillClass: 'vp-verified',
    iconClass: 'rci-verified',
    cardClass: 'rc-verified',
    pillLabel: 'Verified',
    title: 'Certificate Verified',
    description: 'This Research Spectrum certificate is authentic and currently valid.',
  },
  not_found: {
    pillClass: 'vp-not-found',
    iconClass: 'rci-not-found',
    cardClass: 'rc-not-found',
    pillLabel: 'Not Found',
    title: 'Certificate Not Found',
    description:
      'No certificate matching this credential ID was found in the Research Spectrum system. Please check that the ID was entered correctly and try again.',
  },
  revoked: {
    pillClass: 'vp-revoked',
    iconClass: 'rci-revoked',
    cardClass: 'rc-revoked',
    pillLabel: 'Revoked',
    title: 'Certificate Revoked',
    description:
      'This certificate has been revoked and is no longer valid. Contact Research Spectrum support if you have questions.',
  },
  expired: {
    pillClass: 'vp-expired',
    iconClass: 'rci-expired',
    cardClass: 'rc-expired',
    pillLabel: 'Expired',
    title: 'Certificate Expired',
    description:
      'This certificate was previously valid but has passed its validity period. Contact Research Spectrum for information about recertification.',
  },
  pending: {
    pillClass: 'vp-pending',
    iconClass: 'rci-pending',
    cardClass: 'rc-pending',
    pillLabel: 'Processing',
    title: 'Certificate Processing',
    description:
      'This certificate has been issued and is currently being processed for verification. Please check back shortly.',
  },
}

function nowStamp(date = new Date()): string {
  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}, ${hours}:${minutes} UTC`
}

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to verify certificate'
}

function toReady(result: PublicCertificateResult, queryId: string): ReadyView {
  const checkedAt = nowStamp()
  if (result.status === 'not_found') {
    return { status: 'not_found', queryId, checkedAt, cert: null }
  }
  if (result.status === 'valid') {
    return {
      status: 'verified',
      queryId,
      checkedAt,
      cert: {
        name: result.studentName,
        course: result.courseTitle,
        credentialId: result.credentialId,
        issueDate: result.issueDate,
        instructor: result.instructorName?.trim() || DEFAULT_INSTRUCTOR_NAME,
        competencies: COMPETENCIES_BY_COURSE[result.courseTitle] ?? [],
      },
    }
  }
  return {
    status: result.status,
    queryId,
    checkedAt,
    cert: null,
    revokedReason: result.status === 'revoked' ? result.revokedReason : undefined,
  }
}

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

function Icon({ children, strokeWidth = '2', style }: { children: ReactNode; strokeWidth?: string; style?: CSSProperties }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>
      {children}
    </svg>
  )
}

function SearchIcon({ style }: { style?: CSSProperties }) {
  return (
    <Icon style={style}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </Icon>
  )
}

function ArrowIcon({ style }: { style?: CSSProperties }) {
  return (
    <Icon strokeWidth="2.5" style={style}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  )
}

function CheckIcon({ strokeWidth = '2.6', style }: { strokeWidth?: string; style?: CSSProperties }) {
  return (
    <Icon strokeWidth={strokeWidth} style={style}>
      <path d="M20 6 9 17l-5-5" />
    </Icon>
  )
}

function ClockIcon() {
  return (
    <Icon>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </Icon>
  )
}

function ShieldIcon() {
  return (
    <Icon>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </Icon>
  )
}

function UserIcon() {
  return (
    <Icon>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </Icon>
  )
}

function PlusIcon() {
  return (
    <Icon strokeWidth="2.5">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Icon>
  )
}

function PillMark({ status }: { status: UiStatus }) {
  if (status === 'verified') return <CheckIcon strokeWidth="2.5" />
  if (status === 'not_found') {
    return (
      <Icon>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </Icon>
    )
  }
  if (status === 'revoked') {
    return (
      <Icon>
        <circle cx="12" cy="12" r="10" />
        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
      </Icon>
    )
  }
  return <ClockIcon />
}

function CardMark({ status }: { status: UiStatus }) {
  if (status === 'verified') {
    return (
      <Icon>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </Icon>
    )
  }
  if (status === 'not_found') return <SearchIcon />
  if (status === 'revoked') {
    return (
      <Icon>
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </Icon>
    )
  }
  if (status === 'expired') return <ClockIcon />
  return (
    <Icon>
      <path d="M21 12a9 9 0 1 1-9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
    </Icon>
  )
}

function WhyIcon({ name }: { name: (typeof WHY)[number]['icon'] }) {
  if (name === 'shield') return <ShieldIcon />
  if (name === 'check') {
    return (
      <Icon>
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </Icon>
    )
  }
  if (name === 'user') return <UserIcon />
  return <SearchIcon />
}

function VerifyResult({ view }: { view: ReadyView }) {
  const copy = STATUS_COPY[view.status]
  const cert = view.status === 'verified' ? view.cert : null
  return (
    <div className="wrap">
      <div id="statusCard" className={`result-card ${copy.cardClass}`} style={{ maxWidth: 900, margin: '0 auto 22px' }}>
        <div className="rc-head">
          <div className={`rc-status-ic ${copy.iconClass}`}>
            <CardMark status={view.status} />
          </div>
          <div className="rc-head-info">
            <span className={`vcv-pill ${copy.pillClass}`}>
              <PillMark status={view.status} /> {copy.pillLabel}
            </span>
            <h3>{copy.title}</h3>
            <p>{copy.description}</p>
            {view.revokedReason ? (
              <p style={{ marginTop: 8, fontSize: '13.5px', color: '#b91c1c', fontWeight: 700 }}>
                Reason: {view.revokedReason}
              </p>
            ) : null}
          </div>
        </div>
        {cert ? (
          <>
            <div className="rc-details">
              <div className="rc-detail-item">
                <div className="rc-di-label">Certificate Holder</div>
                <div className="rc-di-val">{cert.name}</div>
              </div>
              <div className="rc-detail-item">
                <div className="rc-di-label">Course</div>
                <div className="rc-di-val">{cert.course}</div>
              </div>
              <div className="rc-detail-item">
                <div className="rc-di-label">Credential ID</div>
                <div className="rc-di-val" style={{ fontSize: '12.5px', letterSpacing: '.02em' }}>{cert.credentialId}</div>
              </div>
              <div className="rc-detail-item">
                <div className="rc-di-label">Issue Date</div>
                <div className="rc-di-val">{cert.issueDate}</div>
              </div>
              <div className="rc-detail-item">
                <div className="rc-di-label">Status</div>
                <div className="rc-di-val green">Verified</div>
              </div>
              <div className="rc-detail-item">
                <div className="rc-di-label">Instructor</div>
                <div className="rc-di-val">{cert.instructor}</div>
              </div>
            </div>
            <div className="rc-timestamp">
              <ClockIcon />
              Verified on {view.checkedAt}
            </div>
          </>
        ) : (
          <div className="rc-timestamp">
            <ClockIcon />
            Queried ID: <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--navy)', marginLeft: 4 }}>{view.queryId || '—'}</span>&nbsp;·&nbsp;Checked on {view.checkedAt}
          </div>
        )}
      </div>

      {cert ? (
        <div id="verifiedContent" style={{ maxWidth: 900, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 22, alignItems: 'start' }}>
            <div className="cert-preview-wrap">
              <div className="cert-preview-title">
                <Icon>
                  <circle cx="12" cy="8" r="6" />
                  <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
                </Icon>
                Certificate Preview
              </div>
              <div className="cert-doc">
                <div className="cert-header">
                  <div className="cert-logo-row">
                    <div className="cert-logo-text">
                      <div className="cert-logo-mark">
                        <Icon>
                          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
                          <rect x="9" y="3" width="6" height="4" rx="1" />
                        </Icon>
                      </div>
                      Research Spectrum
                    </div>
                    <div className="cert-badge">Verified</div>
                  </div>
                  <div className="cert-header-title">Certificate of Completion</div>
                  <div className="cert-header-h">{cert.course}</div>
                  <div className="cert-course-pill">
                    <Icon strokeWidth="2" style={{ width: 13, height: 13 }}>
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </Icon>
                    {cert.course}
                  </div>
                </div>
                <div className="cert-body">
                  <div className="cert-recipient-label">This certifies that</div>
                  <div className="cert-recipient-name">{cert.name}</div>
                  <div className="cert-details-row">
                    <div className="cert-detail">
                      <div className="dl">Credential ID</div>
                      <div className="dv" style={{ fontSize: 12 }}>{cert.credentialId}</div>
                    </div>
                    <div className="cert-detail">
                      <div className="dl">Issue Date</div>
                      <div className="dv">{cert.issueDate}</div>
                    </div>
                    <div className="cert-detail">
                      <div className="dl">Status</div>
                      <div className="dv" style={{ color: '#0d6f3e' }}>Verified</div>
                    </div>
                  </div>
                  <div className="cert-footer">
                    <div className="cert-sig">
                      <div className="cert-sig-line" />
                      <div className="cert-sig-name">{cert.instructor}</div>
                      <div className="cert-sig-role">Instructor · Research Spectrum</div>
                    </div>
                    <div className="cert-seal">
                      <Icon strokeWidth="2.2">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        <path d="M9 12l2 2 4-4" />
                      </Icon>
                    </div>
                  </div>
                  <div className="cert-cred-id">
                    Credential ID: {cert.credentialId} · Issued by Research Spectrum · researchspectrum.org/verify/{cert.credentialId}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 20, padding: 22, boxShadow: 'var(--shadow-sm)' }}>
                <h3 style={{ fontSize: 15, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.01em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span style={{ width: 30, height: 30, borderRadius: 9, background: '#dcf5e3', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
                    <CheckIcon strokeWidth="2.5" style={{ width: 14, height: 14, color: '#0d6f3e' }} />
                  </span>
                  Competencies Demonstrated
                </h3>
                <div className="comp-list">
                  {cert.competencies.map((item) => (
                    <div className="comp-item" key={item}>
                      <div className="comp-ic">
                        <CheckIcon />
                      </div>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 20, padding: 22, boxShadow: 'var(--shadow-sm)' }}>
                <h3 style={{ fontSize: 15, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.01em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--sky)', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
                    <ArrowIcon style={{ width: 14, height: 14, color: 'var(--blue)' }} />
                  </span>
                Certificate Journey
                </h3>
                <div className="pathway-wrap" style={{ maxWidth: '100%' }}>
                  <div className="pathway-line" />
                  {JOURNEY.map(([title, body]) => (
                    <div className="pathway-step" key={title}>
                      <div className="path-node done">
                        <CheckIcon style={{ width: 18, height: 18 }} />
                      </div>
                      <div className="path-info">
                        <h4 style={{ fontSize: 14 }}>{title}</h4>
                        <p style={{ fontSize: '12.5px' }}>{body}</p>
                      </div>
                    </div>
                  ))}
                  <div className="pathway-step">
                    <div className="path-node" style={{ fontSize: 11, fontWeight: 800, background: 'var(--grad-cta)' }}>
                      <SearchIcon style={{ width: 16, height: 16 }} />
                    </div>
                    <div className="path-info">
                      <h4 style={{ fontSize: 14, color: 'var(--blue)' }}>Verification</h4>
                      <p style={{ fontSize: '12.5px' }}>Currently verified</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default function VerifyCertificatePage() {
  usePageTitle('Certificate Verification')
  const { credentialId: routeCredentialId } = useParams<{ credentialId?: string }>()
  const navigate = useNavigate()
  const rootRef = useRef<HTMLDivElement>(null)
  const resultRef = useRef<HTMLElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const requestSeq = useRef(0)
  const errTimer = useRef<number | undefined>(undefined)
  const [inputValue, setInputValue] = useState(routeCredentialId ?? '')
  const [inputErr, setInputErr] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  const [phase, setPhase] = useState<Phase>(routeCredentialId ? { status: 'loading' } : { status: 'idle' })

  useReveal(rootRef)

  const lookup = useCallback(async (credentialId: string) => {
    const trimmed = credentialId.trim()
    if (!trimmed) {
      setPhase({ status: 'idle' })
      return
    }
    const seq = ++requestSeq.current
    setPhase({ status: 'loading' })
    try {
      const result = await getPublicCertificate(trimmed)
      if (seq !== requestSeq.current) return
      setPhase({ status: 'ready', view: toReady(result, trimmed) })
    } catch (err) {
      if (seq !== requestSeq.current) return
      setPhase({ status: 'error', message: errorMessage(err) })
    }
  }, [])

  useEffect(() => {
    setInputValue(routeCredentialId ?? '')
    if (!routeCredentialId) {
      requestSeq.current += 1
      setPhase({ status: 'idle' })
      return
    }
    const seq = ++requestSeq.current
    setPhase({ status: 'loading' })
    void getPublicCertificate(routeCredentialId)
      .then((result) => {
        if (seq !== requestSeq.current) return
        setPhase({ status: 'ready', view: toReady(result, routeCredentialId) })
      })
      .catch((err: unknown) => {
        if (seq !== requestSeq.current) return
        setPhase({ status: 'error', message: errorMessage(err) })
      })
  }, [routeCredentialId])

  useEffect(() => {
    if (phase.status !== 'ready') return
    const node = resultRef.current
    if (!node || typeof node.scrollIntoView !== 'function') return
    const timer = window.setTimeout(() => {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)
    return () => window.clearTimeout(timer)
  }, [phase])

  useEffect(() => () => window.clearTimeout(errTimer.current), [])

  function markEmpty() {
    setInputErr(true)
    inputRef.current?.focus()
    window.clearTimeout(errTimer.current)
    errTimer.current = window.setTimeout(() => setInputErr(false), 1200)
  }

  function onVerify() {
    if (phase.status === 'loading') return
    const trimmed = inputValue.trim()
    if (!trimmed) {
      markEmpty()
      return
    }
    if (trimmed === (routeCredentialId ?? '')) {
      void lookup(trimmed)
      return
    }
    void navigate(`/verify/${encodeURIComponent(trimmed)}`)
  }

  function onClear() {
    setInputValue('')
    setInputErr(false)
    requestSeq.current += 1
    setPhase({ status: 'idle' })
    if (routeCredentialId) {
      void navigate('/verify')
    }
  }

  const loading = phase.status === 'loading'
  const showClear = inputValue.length > 0 && !loading

  return (
    <div ref={rootRef} className="pg-verify" data-testid="student-page-verify-certificate">
      <section className="cv-hero">
        <div className="wrap">
          <div className="eyebrow reveal"><span className="dot" />Certificate Verification</div>
          <h1 className="reveal" data-d="1">Verify <span className="g">Certificate</span><br />Authenticity</h1>
          <p className="sub reveal" data-d="2">Instantly verify the status and validity of Research Spectrum competency-based certificates using a unique credential ID.</p>
          <div className="search-card reveal" data-d="3">
            <div className="sc-title">
              <SearchIcon />
              Enter Certificate ID
            </div>
            <div className="search-row">
              <input
                ref={inputRef}
                type="text"
                className={inputErr ? 'search-input err' : 'search-input'}
                id="certInput"
                placeholder="e.g. RS-RM-2026-A1B7F3"
                autoComplete="off"
                spellCheck={false}
                aria-label="Certificate ID"
                aria-describedby="searchHint"
                value={inputValue}
                onChange={(event) => {
                  setInputValue(event.target.value)
                  setInputErr(false)
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') onVerify()
                }}
              />
              <button type="button" className="btn btn-primary" id="verifyBtn" disabled={loading} onClick={onVerify}>
                <span id="verifyBtnTxt">{loading ? 'Verifying…' : 'Verify Certificate'}</span>
                <div className={loading ? 'btn-spinner v' : 'btn-spinner'} id="verifySpinner" aria-hidden="true" />
                <svg id="verifyArrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={loading ? { display: 'none' } : undefined}>
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </button>
              <button type="button" className="btn btn-ghost" id="clearBtn" style={{ display: showClear ? undefined : 'none' }} aria-label="Clear search" onClick={onClear}>
                <Icon strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </Icon>
              </button>
            </div>
            <p className="sc-hint" id="searchHint">
              Use the credential ID printed on your certificate, or found on your <Link to="/certificates">Certificates</Link> page.
            </p>
            {phase.status === 'error' ? (
              <p className="sc-hint" role="alert" style={{ color: '#b91c1c' }}>{phase.message}</p>
            ) : null}
          </div>
        </div>
      </section>

      <section id="resultSection" className={phase.status === 'ready' ? 'show' : undefined} ref={resultRef}>
        {phase.status === 'ready' ? <VerifyResult view={phase.view} /> : null}
      </section>

      <section className="sec" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Why It Matters</p>
            <h2 className="title">The Value of Verified Credentials</h2>
            <p className="lead" style={{ maxWidth: 760 }}>Research Spectrum certificates are competency-based completion certificates — awarded after successful completion of course requirements and assessment criteria, so every verified credential reflects real, assessed capability.</p>
          </div>
          <div className="why-grid">
            {WHY.map((card, index) => (
              <div className="why-card reveal" data-d={String(index + 1)} key={card.title}>
                <div className="why-ic"><WhyIcon name={card.icon} /></div>
                <h3>{card.title}</h3>
                <p>{card.body}</p>
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
          <div className="rt-faq-list reveal">
            {FAQ.map((item, index) => {
              const open = openFaq === index
              return (
                <div className={open ? 'rt-faq-item open' : 'rt-faq-item'} key={item.question}>
                  <button className="rt-faq-q" type="button" aria-expanded={open} onClick={() => setOpenFaq(open ? null : index)}>
                    <h3>{item.question}</h3>
                    <div className="rt-faq-ic"><PlusIcon /></div>
                  </button>
                  <div className="rt-faq-a"><p>{item.answer}</p></div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingBottom: 80 }}>
        <div className="wrap">
          <div className="support-card reveal">
            <div className="support-ic">
              <Icon>
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </Icon>
            </div>
            <div className="support-body">
              <h3>Verification Support</h3>
              <p>If you believe a certificate has been issued incorrectly, cannot be verified as expected, or you have questions about the verification process, the Research Spectrum team is available to assist.</p>
            </div>
            <div className="support-actions">
              <Link to="/contact" className="btn btn-primary btn-sm">Contact Support <ArrowIcon /></Link>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingBottom: 88, paddingTop: 0 }}>
        <div className="wrap">
          <div className="rt-cta reveal">
            <p className="kicker" style={{ color: 'rgba(255,255,255,.75)', marginBottom: 14 }}>Get Started</p>
            <h2>Build Research Skills That Can Be Verified</h2>
            <p>Join Research Spectrum and earn competency-based certificates that demonstrate real research capability to the people who matter.</p>
            <div className="btn-w">
              <Link to="/courses#courses-catalog" className="btn btn-white">Explore Courses <ArrowIcon /></Link>
              <Link to="/about" className="btn" style={{ background: 'rgba(255,255,255,.14)', color: '#fff', border: '1.5px solid rgba(255,255,255,.22)' }}>Meet The Instructor</Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
