import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import { submitPublicContact } from '../lib/api/public-contact'
import { legalConfig } from '../lib/legalConfig'
import {
  contactCategories,
  contactChannels,
  contactFormCopy,
  contactHero,
} from '../lib/marketing/contactCopy'
import { usePageTitle } from '../lib/page-title'
import './ContactPage.css'

const INSTAGRAM_HREF = 'https://www.instagram.com/researchspectrum/'

const inlineLinkStyle = { color: 'var(--blue)', fontWeight: 700 }

type FormStatus = { kind: 'success' | 'error'; message: string }

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

function Icon({ children, strokeWidth = '2' }: { children: ReactNode; strokeWidth?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  )
}

function ArrowIcon() {
  return (
    <Icon strokeWidth="2.5">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  )
}

function CheckIcon({ strokeWidth = '2.8' }: { strokeWidth?: string }) {
  return (
    <Icon strokeWidth={strokeWidth}>
      <path d="M20 6 9 17l-5-5" />
    </Icon>
  )
}

function MailIcon() {
  return (
    <Icon>
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </Icon>
  )
}

function CopyIcon() {
  return (
    <Icon>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </Icon>
  )
}

function InstagramIcon() {
  return (
    <Icon>
      <rect x="2" y="2" width="20" height="20" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1.5" fill="currentColor" stroke="none" />
    </Icon>
  )
}

function ExternalIcon() {
  return (
    <Icon>
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </Icon>
  )
}

function WhatsAppIcon() {
  return (
    <Icon>
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </Icon>
  )
}

function ChatIcon() {
  return (
    <Icon>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
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

function FormAlertIcon() {
  return (
    <Icon>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </Icon>
  )
}

function MailLink() {
  return (
    <a href={`mailto:${legalConfig.supportEmail}`} style={inlineLinkStyle}>
      {legalConfig.supportEmail}
    </a>
  )
}

function InstagramHandleLink() {
  return (
    <a href={INSTAGRAM_HREF} target="_blank" rel="noopener noreferrer" style={inlineLinkStyle}>
      @researchspectrum
    </a>
  )
}

const faqs: { q: string; a: ReactNode }[] = [
  {
    q: 'How long does support take to respond?',
    a: 'The Research Spectrum support team aims to respond to all messages within 1–2 business days. More complex issues — such as certificate errors, payment disputes, or technical investigations — may require additional time. You will receive a reference number immediately upon submission, which can be used to follow up if needed.',
  },
  {
    q: 'Can I ask course-specific questions through this form?',
    a: 'Yes. Select "Course Support" from the category dropdown and include the course name, module or lesson number, and a clear description of your question. Our team includes subject matter experts who handle research methodology, statistics, scientific writing, and systematic review questions.',
  },
  {
    q: 'Can I submit screenshots or files with my message?',
    a: 'Yes. The contact form includes an optional file attachment field that accepts PDF, DOCX, PNG, JPG, and ZIP files up to 10 MB. For technical issues, attaching a screenshot of the error message significantly speeds up the resolution process. For assignment or certificate queries, attach the relevant document.',
  },
  {
    q: 'How do I update my account information?',
    a: 'Most account information can be updated directly from the Account page in your dashboard — including your name, email, institution, and profession. If you encounter issues updating your information, or if your name needs to be updated on an already-issued certificate, contact support using the "General Question" category.',
  },
  {
    q: 'How do certificate verification issues work?',
    a: (
      <>
        Certificate verification is available at{' '}
        <Link to="/verify" style={inlineLinkStyle}>
          researchspectrum.org/verify
        </Link>
        . If a certificate cannot be verified, or if the verification result does not match the certificate, contact support using the &quot;Certificate Support&quot; category, and include the credential ID printed on the certificate document.
      </>
    ),
  },
  {
    q: 'Who should contact Research Team support?',
    a: 'Students who have already submitted a Research Team application and have questions about the status, interview scheduling, or acceptance decisions should select "Research Team" from the category dropdown. General eligibility questions are answered on the Research Team page and in the FAQ section there.',
  },
  {
    q: 'Can I request a refund?',
    a: (
      <>
        Refund requests should be submitted via the contact form using the &quot;Billing Question&quot; category. Include your course name, purchase date, and the reason for the refund request. Refund eligibility is governed by the Research Spectrum Refund Policy, which is available at{' '}
        <Link to="/refund" style={inlineLinkStyle}>
          RefundPolicy.html
        </Link>
        .
      </>
    ),
  },
  {
    q: 'How do I report a technical issue?',
    a: 'Select "Technical Issue" from the category dropdown. Include your device type, browser and version, the steps that led to the error, the exact error message if one appears, and a screenshot if possible. The more detail you provide, the faster our technical team can investigate and resolve the issue.',
  },
  {
    q: 'How can I contact Research Spectrum directly?',
    a: (
      <>
        You can contact Research Spectrum through the contact form on this page, by emailing <MailLink /> directly, or via our official Instagram account <InstagramHandleLink />. We typically respond within 1–2 business days.
      </>
    ),
  },
  {
    q: 'Do you provide support through WhatsApp?',
    a: (
      <>
        WhatsApp support is currently being prepared and is not yet live. In the meantime, please use email at <MailLink /> or the contact form for all enquiries — these channels are monitored and ensure your request is properly tracked.
      </>
    ),
  },
  {
    q: 'Can I contact Research Spectrum through Instagram?',
    a: (
      <>
        Yes. You can reach Research Spectrum through our Instagram account <InstagramHandleLink /> for general enquiries, platform updates, and announcements. For course-specific support, assignment questions, certificate issues, or technical problems, please use email or the contact form to ensure your request is properly tracked and responded to.
      </>
    ),
  },
]

function outcomeToMessage(outcome: Awaited<ReturnType<typeof submitPublicContact>>): string {
  switch (outcome) {
    case 'accepted':
      return contactFormCopy.successStatus
    case 'validation_error':
      return contactFormCopy.validationErrorStatus
    case 'rate_limited':
      return contactFormCopy.rateLimitStatus
    case 'unavailable':
    case 'unexpected':
      return contactFormCopy.unavailableStatus
  }
}

export default function ContactPage() {
  usePageTitle('Contact')

  const rootRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<FormStatus | null>(null)
  const [copied, setCopied] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  useReveal(rootRef)

  async function handleCopyEmail() {
    try {
      await navigator.clipboard.writeText(legalConfig.supportEmail)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    setStatus(null)

    const form = event.currentTarget
    const data = new FormData(form)
    const name = String(data.get('name') ?? '').trim()
    const email = String(data.get('email') ?? '').trim()
    const category = String(data.get('category') ?? '').trim()
    const subject = String(data.get('subject') ?? '').trim()
    const message = String(data.get('message') ?? '').trim()
    const rs_hp = String(data.get('rs_hp') ?? '')

    setSubmitting(true)
    try {
      const outcome = await submitPublicContact({
        name,
        email,
        category,
        subject,
        message,
        rs_hp,
      })
      if (outcome === 'accepted') {
        form.reset()
        setStatus({ kind: 'success', message: contactFormCopy.successStatus })
      } else {
        setStatus({ kind: 'error', message: outcomeToMessage(outcome) })
      }
    } catch {
      setStatus({ kind: 'error', message: contactFormCopy.unavailableStatus })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div ref={rootRef} className="pg-contact" data-testid="student-page-contact">
      <section className="ct-hero">
        <div className="wrap">
          <div className="ct-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal"><span className="dot"></span>{contactHero.eyebrow}</div>
              <h1 className="reveal" data-d="1">
                {contactHero.titleLine1}
                <br />
                <span className="g">{contactHero.titleHighlight}</span>
              </h1>
              <p className="sub reveal" data-d="2">{contactHero.sub}</p>
              <ul className="trust-list reveal" data-d="3">
                {contactHero.trustItems.map((item) => (
                  <li key={item}>
                    <span className="ck"><CheckIcon /></span>
                    {item}
                  </li>
                ))}
              </ul>
              <div className="hero-ctas reveal" data-d="4">
                <a href="#contactForm" className="btn btn-primary">
                  {contactHero.primaryCta} <ArrowIcon />
                </a>
                <Link to="/faq" className="btn btn-ghost">{contactHero.secondaryCta}</Link>
              </div>
            </div>
            <div className="reveal" data-d="2">
              <div className="support-overview-card">
                <p className="soc-title">{contactHero.overview.title}</p>
                {contactHero.overview.rows.map((row) => (
                  <div className="soc-row" key={row.label}>
                    <span className="soc-label">{row.label}</span>
                    <span className="soc-val">
                      {row.label === 'Support Channels' ? 'Email • Contact Form • Instagram' : row.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingTop: 56, paddingBottom: 56 }}>
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 32 }}>
            <p className="kicker">{contactChannels.kicker}</p>
            <h2 className="title">{contactChannels.title}</h2>
            <p className="lead">{contactChannels.lead}</p>
          </div>
          <div className="cd-grid-3 reveal">
            <div className="cd-item">
              <div className="cd-ic"><MailIcon /></div>
              <div className="cd-label">{contactChannels.email.label}</div>
              <div className="cd-val" style={{ fontSize: 13, letterSpacing: '-.01em', wordBreak: 'break-all' }}>{legalConfig.supportEmail}</div>
              <div className="cd-sub" style={{ marginBottom: 14 }}>{contactChannels.email.sub}</div>
              <button type="button" className={copied ? 'cd-cta copied' : 'cd-cta'} id="copyEmailBtn" onClick={() => { void handleCopyEmail() }}>
                {copied ? <CheckIcon strokeWidth="2.5" /> : <CopyIcon />}
                <span id="copyEmailTxt">{copied ? 'Copied \u2713' : contactChannels.email.copyLabel}</span>
              </button>
            </div>

            <div className="cd-item">
              <div className="cd-ic"><InstagramIcon /></div>
              <div className="cd-label">Instagram</div>
              <div className="cd-val">@researchspectrum</div>
              <div className="cd-sub" style={{ marginBottom: 14 }}>Updates, educational content, announcements, and community engagement.</div>
              <a href={INSTAGRAM_HREF} target="_blank" rel="noopener noreferrer" className="cd-cta">
                <ExternalIcon />
                Visit Instagram
              </a>
            </div>

            <div className="cd-item">
              <div className="cd-ic"><WhatsAppIcon /></div>
              <div className="cd-label">WhatsApp Support</div>
              <div className="cd-val" style={{ fontSize: 13 }}>Coming soon</div>
              <div className="cd-sub" style={{ marginBottom: 14 }}>This channel is being prepared and is not yet live. Until it launches, please use email or the contact form.</div>
              <span className="cd-cta" aria-disabled="true" style={{ opacity: 0.55, cursor: 'not-allowed' }}>Coming Soon</span>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" id="contactForm" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 36 }}>
            <p className="kicker">{contactFormCopy.kicker}</p>
            <h2 className="title">{contactFormCopy.title}</h2>
            <p className="lead">{contactFormCopy.lead}</p>
          </div>
          <div style={{ maxWidth: 820, margin: '0 auto' }}>
            <div className="form-card reveal">
              {status?.kind === 'success' ? (
                <div className="form-success show" id="formSuccess">
                  <div className="fs-ic"><CheckIcon strokeWidth="2.5" /></div>
                  <div className="fs-title">Message Sent Successfully</div>
                  <p className="fs-body" role="status">{status.message}</p>
                  <div className="fs-actions">
                    <button type="button" className="btn btn-primary" id="sendAnotherBtn" onClick={() => setStatus(null)}>
                      Send Another Message <ArrowIcon />
                    </button>
                    <Link to="/dashboard" className="btn btn-ghost" id="dashboardBtn">My Dashboard</Link>
                  </div>
                </div>
              ) : (
                <div id="formState">
                  <h3 className="fc-title">
                    <span className="fc-ic"><ChatIcon /></span>
                    {contactFormCopy.formTitle}
                  </h3>
                  <p className="fc-sub">{contactFormCopy.formSub}</p>
                  <div id="authBadge" style={{ display: 'none' }} className="auth-badge">
                    <span className="ab-dot"></span>
                    <span>Signed in as: <b id="authName">—</b></span>
                  </div>
                  <form id="contactFormEl" onSubmit={(event) => { void handleSubmit(event) }} noValidate autoComplete="on">
                    <input className="hp" type="text" name="rs_hp" tabIndex={-1} autoComplete="off" aria-hidden="true" defaultValue="" />
                    <div className="field-grid">
                      <div className="field" id="fName">
                        <label htmlFor="ctName">{contactFormCopy.nameLabel}</label>
                        <input type="text" id="ctName" name="name" placeholder={contactFormCopy.namePlaceholder} autoComplete="name" aria-describedby="eName" aria-required="true" disabled={submitting} />
                        <span className="err-msg" id="eName" role="alert"></span>
                      </div>
                      <div className="field" id="fEmail">
                        <label htmlFor="ctEmail">{contactFormCopy.emailLabel}</label>
                        <input type="email" id="ctEmail" name="email" placeholder={contactFormCopy.emailPlaceholder} autoComplete="email" inputMode="email" aria-describedby="eEmail" aria-required="true" disabled={submitting} />
                        <span className="err-msg" id="eEmail" role="alert"></span>
                      </div>
                    </div>
                    <div className="field-grid">
                      <div className="field" id="fCategory">
                        <label htmlFor="ctCategory">{contactFormCopy.categoryLabel}</label>
                        <select id="ctCategory" name="category" aria-describedby="eCategory" aria-required="true" defaultValue="" disabled={submitting}>
                          <option value="">{contactFormCopy.categoryPlaceholder}</option>
                          {contactCategories.map((category) => (
                            <option key={category}>{category}</option>
                          ))}
                        </select>
                        <span className="err-msg" id="eCategory" role="alert"></span>
                      </div>
                      <div className="field" id="fSubject">
                        <label htmlFor="ctSubject">{contactFormCopy.subjectLabel}</label>
                        <input type="text" id="ctSubject" name="subject" placeholder={contactFormCopy.subjectPlaceholder} aria-describedby="eSubject" aria-required="true" disabled={submitting} />
                        <span className="err-msg" id="eSubject" role="alert"></span>
                      </div>
                    </div>
                    <div className="field" id="fMessage">
                      <label htmlFor="ctMessage">{contactFormCopy.messageLabel}</label>
                      <textarea id="ctMessage" name="message" placeholder={contactFormCopy.messagePlaceholder} rows={5} aria-describedby="eMessage" aria-required="true" disabled={submitting}></textarea>
                      <span className="err-msg" id="eMessage" role="alert"></span>
                    </div>
                    {status?.kind === 'error' ? (
                      <div className="form-err visible" id="formErr" role="status" aria-live="polite"><FormAlertIcon /><span id="formErrText">{status.message}</span></div>
                    ) : null}
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                      <button type="submit" className="btn btn-primary" id="submitBtn" disabled={submitting}>
                        <span id="submitBtnTxt">{submitting ? 'Sending\u2026' : contactFormCopy.submitLabel}</span>
                        <div className={submitting ? 'btn-spinner v' : 'btn-spinner'} id="submitSpinner" aria-hidden="true" />
                        {submitting ? null : <ArrowIcon />}
                      </button>
                      <span style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600 }}>{contactFormCopy.responseNote}</span>
                    </div>
                  </form>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingTop: 72, paddingBottom: 72 }}>
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 32 }}>
            <p className="kicker">Faster Support</p>
            <h2 className="title">What to Include in Your Message</h2>
            <p className="lead">Including the right information helps us resolve your question faster. Here&apos;s what to include for each topic.</p>
          </div>
          <div className="guidance-grid">
            <div className="guidance-card reveal" data-d="1">
              <div className="gc-ic">
                <Icon>
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </Icon>
              </div>
              <h3>Course Questions</h3>
              <ul>
                <li>Course name</li>
                <li>Module or lesson number</li>
                <li>Your specific question</li>
                <li>What you&apos;ve already tried</li>
              </ul>
            </div>
            <div className="guidance-card reveal" data-d="2">
              <div className="gc-ic">
                <Icon>
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </Icon>
              </div>
              <h3>Assignment Support</h3>
              <ul>
                <li>Course name</li>
                <li>Assignment title</li>
                <li>Issue encountered</li>
                <li>Screenshots if applicable</li>
              </ul>
            </div>
            <div className="guidance-card reveal" data-d="3">
              <div className="gc-ic">
                <Icon>
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </Icon>
              </div>
              <h3>Technical Issues</h3>
              <ul>
                <li>Device and browser used</li>
                <li>Error message text</li>
                <li>Steps to reproduce</li>
                <li>Screenshot of the issue</li>
              </ul>
            </div>
            <div className="guidance-card reveal" data-d="4">
              <div className="gc-ic">
                <Icon>
                  <circle cx="12" cy="8" r="6" />
                  <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
                </Icon>
              </div>
              <h3>Certificates &amp; Verification</h3>
              <ul>
                <li>Credential ID from certificate</li>
                <li>Course name</li>
                <li>Issue description</li>
                <li>Intended use for verification</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingTop: 72, paddingBottom: 72 }}>
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 32 }}>
            <p className="kicker">Self-Service</p>
            <h2 className="title">Before Contacting Support</h2>
            <p className="lead">Many questions are already answered on the platform. Check these pages first — it&apos;s often the fastest way to find what you need.</p>
          </div>
          <div className="hc-grid-4 reveal">
            <Link to="/faq" className="hc-card">
              <div className="hc-ic">
                <Icon>
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </Icon>
              </div>
              <span>Browse FAQ</span>
              <small>Answers to common questions</small>
            </Link>
            <Link to="/certificates" className="hc-card">
              <div className="hc-ic">
                <Icon>
                  <circle cx="12" cy="8" r="6" />
                  <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
                </Icon>
              </div>
              <span>Certificates</span>
              <small>Your certificates and verification</small>
            </Link>
            <Link to="/research-team" className="hc-card">
              <div className="hc-ic">
                <Icon>
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                </Icon>
              </div>
              <span>Research Team</span>
              <small>Eligibility and application info</small>
            </Link>
            <Link to="/account/profile" className="hc-card">
              <div className="hc-ic">
                <Icon>
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </Icon>
              </div>
              <span>Account Settings</span>
              <small>Manage your account details</small>
            </Link>
          </div>
        </div>
      </section>

      <section className="sec" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)', paddingTop: 72, paddingBottom: 72 }}>
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 48 }}>
            <p className="kicker">The Process</p>
            <h2 className="title">How Support Works</h2>
          </div>
          <div className="process-grid reveal">
            <div className="process-step">
              <div className="ps-node">1</div>
              <h3>Submit Request</h3>
              <p>Provide details about your question or issue.</p>
            </div>
            <div className="process-step">
              <div className="ps-node">2</div>
              <h3>Review</h3>
              <p>The appropriate team member reviews your request.</p>
            </div>
            <div className="process-step">
              <div className="ps-node">3</div>
              <h3>Response</h3>
              <p>A detailed response is sent to your email.</p>
            </div>
            <div className="process-step">
              <div className="ps-node">4</div>
              <h3>Resolution</h3>
              <p>We work with you until the issue is resolved.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" id="faq">
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 40 }}>
            <p className="kicker">Common Questions</p>
            <h2 className="title">Frequently Asked Questions</h2>
          </div>
          <div className="rt-faq-list reveal">
            {faqs.map((item, index) => {
              const isOpen = openFaq === index
              return (
                <div className={isOpen ? 'rt-faq-item open' : 'rt-faq-item'} key={item.q}>
                  <button
                    className="rt-faq-q"
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => setOpenFaq(isOpen ? null : index)}
                  >
                    <h3>{item.q}</h3>
                    <div className="rt-faq-ic"><PlusIcon /></div>
                  </button>
                  <div className="rt-faq-a"><p>{item.a}</p></div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingBottom: 88, paddingTop: 0 }}>
        <div className="wrap">
          <div className="rt-cta reveal">
            <p className="kicker" style={{ color: 'rgba(255,255,255,.75)', marginBottom: 14 }}>We&apos;re Here to Help</p>
            <h2>Need Help With Your Research Journey?</h2>
            <p>Whether you&apos;re learning research methodology, statistics, scientific writing, systematic reviews, or working toward the Research Team — we&apos;re here to support your progress.</p>
            <div className="btn-w" id="ctaBtns">
              <Link to="/faq" className="btn btn-white" id="ctaPrimary">
                <span id="ctaPrimaryTxt">Browse FAQ</span> <ArrowIcon />
              </Link>
              <Link to="/courses#courses-catalog" className="btn" id="ctaAlt" style={{ background: 'rgba(255,255,255,.14)', color: '#fff', border: '1.5px solid rgba(255,255,255,.22)' }}>
                Explore Courses
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
