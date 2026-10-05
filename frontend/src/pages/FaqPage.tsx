import { Fragment, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import { usePageTitle } from '../lib/page-title'
import { faqEntries, type FaqEntry, type FaqPart } from './faq/faqEntries'
import './FaqPage.css'

const linkStyle = { color: 'var(--blue)', fontWeight: 700 } as const

const SECTIONS: ReadonlyArray<{
  id: string
  title: string
  tag?: string
  minor?: boolean
  count: number
}> = [
  { id: 'getting-started', title: 'Getting Started', tag: 'Start Here', count: 6 },
  { id: 'courses', title: 'Courses', tag: 'Key Topic', count: 6 },
  { id: 'quizzes-assignments', title: 'Quizzes & Assignments', count: 8 },
  { id: 'certificates', title: 'Certificates', tag: 'Key Topic', count: 7 },
  { id: 'research-team', title: 'Research Team', tag: 'Key Topic', count: 7 },
  { id: 'purchases', title: 'Purchases & Payments', count: 6 },
  { id: 'account', title: 'Account & Settings', minor: true, count: 6 },
  { id: 'support', title: 'Support', minor: true, count: 6 },
]

const PATHWAY = [
  ['Course Enrollment', 'Purchase an individual course or the Research Mastery Bundle. Access begins immediately after checkout.'],
  ['Learning Modules', 'Work through expert-led video lectures, readings, and practical exercises at your own pace — no deadlines.'],
  ['Module Quizzes', 'Complete mastery-based knowledge checks after each module. Retake as many times as needed — no limits.'],
  ['Final Assignment', 'Apply course skills to a real dataset or research scenario. Receive detailed evaluator feedback on every submission.'],
  ['Certificate Awarded', 'Pass the assignment (70%+) and your verified Research Spectrum certificate is issued automatically.'],
  ['Research Team Eligibility', 'Earn all four course certificates and you become eligible to apply for the Research Spectrum Research Team — contributing to published research.'],
] as const

const TRUST = [
  'Course & Certificate Guidance',
  'Research Team Eligibility',
  'Quiz & Assignment Support',
  'Verified Credentials',
] as const

const BEYOND = [
  'Complete all four certificates',
  'Become eligible to apply',
  'Join real research projects',
  'Contribute to publishable work',
  'Earn authorship through meaningful contributions',
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

function Icon({ children, strokeWidth = '2' }: { children: ReactNode; strokeWidth?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  )
}

function CheckIcon() {
  return (
    <Icon strokeWidth="2.8">
      <path d="M20 6 9 17l-5-5" />
    </Icon>
  )
}

function ArrowIcon({ style }: { style?: CSSProperties }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
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

function ShieldIcon({ strokeWidth = '2.5' }: { strokeWidth?: string }) {
  return (
    <Icon strokeWidth={strokeWidth}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </Icon>
  )
}

function SearchIcon({ strokeWidth = '2' }: { strokeWidth?: string }) {
  return (
    <Icon strokeWidth={strokeWidth}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </Icon>
  )
}

function StartedIcon() {
  return (
    <Icon>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </Icon>
  )
}

function CoursesIcon() {
  return (
    <Icon>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </Icon>
  )
}

function QuizIcon() {
  return (
    <Icon>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
    </Icon>
  )
}

function CertIcon() {
  return (
    <Icon>
      <circle cx="12" cy="8" r="6" />
      <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
    </Icon>
  )
}

function TeamIcon() {
  return (
    <Icon>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </Icon>
  )
}

function PayIcon() {
  return (
    <Icon>
      <rect x="1" y="4" width="22" height="16" rx="2" />
      <line x1="1" y1="10" x2="23" y2="10" />
    </Icon>
  )
}

function AccountIcon() {
  return (
    <Icon>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </Icon>
  )
}

function SupportIcon() {
  return (
    <Icon>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
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

const SECTION_ICONS: Record<string, () => ReactNode> = {
  'getting-started': StartedIcon,
  courses: CoursesIcon,
  'quizzes-assignments': QuizIcon,
  certificates: CertIcon,
  'research-team': TeamIcon,
  purchases: PayIcon,
  account: AccountIcon,
  support: SupportIcon,
}

function AnswerParts({ parts }: { parts: FaqPart[] }) {
  return (
    <>
      {parts.map((part, index) => {
        if (typeof part === 'string') return <Fragment key={index}>{part}</Fragment>
        if ('strong' in part) return <strong key={index}>{part.strong}</strong>
        if (part.external) {
          return (
            <a
              key={index}
              href={part.href}
              style={linkStyle}
              {...(part.blank ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
            >
              {part.label}
            </a>
          )
        }
        return (
          <Link key={index} to={part.href} style={linkStyle}>
            {part.label}
          </Link>
        )
      })}
    </>
  )
}

function TrustList({ items, style, reveal }: { items: readonly string[]; style?: CSSProperties; reveal?: string }) {
  return (
    <ul className={reveal ? 'trust-list reveal' : 'trust-list'} style={style} data-d={reveal}>
      {items.map((item) => (
        <li key={item}>
          <span className="ck"><CheckIcon /></span>
          {item}
        </li>
      ))}
    </ul>
  )
}

function itemMatches(item: FaqEntry, query: string): boolean {
  if (!query) return true
  const haystack = `${item.dataQ} ${item.question} ${item.plain}`.toLowerCase()
  return haystack.includes(query)
}

const GROUPED = SECTIONS.reduce<Array<(typeof SECTIONS)[number] & { items: FaqEntry[] }>>(
  (groups, section) => {
    const start = groups.reduce((sum, group) => sum + group.count, 0)
    groups.push({ ...section, items: faqEntries.slice(start, start + section.count) })
    return groups
  },
  [],
)

export default function FaqPage() {
  usePageTitle('FAQ')
  const rootRef = useRef<HTMLDivElement>(null)
  useReveal(rootRef)
  const [query, setQuery] = useState('')
  const [openIds, setOpenIds] = useState<Set<string>>(() => new Set())
  const [highlightId, setHighlightId] = useState<string | null>(null)
  const [activeCat, setActiveCat] = useState('getting-started')

  const normalized = query.trim().toLowerCase()
  const grouped = GROUPED

  const found = useMemo(
    () => faqEntries.filter((item) => itemMatches(item, normalized)).length,
    [normalized],
  )

  useEffect(() => {
    const onScroll = () => {
      const scrollY = window.scrollY + 200
      let current: string | null = null
      for (const section of SECTIONS) {
        const el = document.getElementById(`cat-${section.id}`)
        if (!el) continue
        if (el.getBoundingClientRect().top + window.scrollY - 200 <= scrollY) current = section.id
      }
      if (current) setActiveCat(current)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  function toggleItem(id: string) {
    setOpenIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function jumpToQ(id: string) {
    const el = document.getElementById(id)
    if (!el) return
    const offset = el.getBoundingClientRect().top + window.scrollY - 160
    window.scrollTo({ top: offset, behavior: 'smooth' })
    window.setTimeout(() => {
      setOpenIds((prev) => new Set(prev).add(id))
      setHighlightId(id)
      window.setTimeout(() => {
        setHighlightId((current) => (current === id ? null : current))
      }, 2500)
    }, 500)
  }

  function selectCategory(cat: string) {
    setActiveCat(cat)
    const target = document.getElementById(`cat-${cat}`)
    if (!target) return
    const offset = target.getBoundingClientRect().top + window.scrollY - 150
    window.scrollTo({ top: offset, behavior: 'smooth' })
  }

  return (
    <div ref={rootRef} className="pg-faq" data-testid="student-page-faq">
      <section className="faq-hero">
        <div className="wrap">
          <div className="faq-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal"><span className="dot" />Research Spectrum Guidance Center</div>
              <h1 className="reveal" data-d="1">Questions About<br /><span className="g">Learning Research?</span></h1>
              <p className="sub reveal" data-d="2">Answers about courses, certificates, assessments, and Research Team eligibility — everything you need to navigate your Research Spectrum journey with confidence.</p>
              <TrustList items={TRUST} reveal="3" />
              <div className="hero-ctas reveal" data-d="4">
                <Link to="/courses#courses-catalog" className="btn btn-primary">Explore Courses <ArrowIcon /></Link>
                <Link to="/verify" className="btn btn-ghost">Verify A Certificate <ShieldIcon /></Link>
                <Link to="/contact" className="btn btn-ghost">Contact Support</Link>
              </div>
            </div>
            <div className="reveal" data-d="2">
              <div className="kb-card">
                <div className="kb-title">Research Spectrum Support</div>
                <div className="kb-row"><span className="kb-label">Average Response Time</span><span className="kb-val"><span className="kb-pill">1–2 Business Days</span></span></div>
                <div className="kb-row">
                  <span className="kb-label">Certificate Verification</span>
                  <span className="kb-val">
                    <Link to="/verify" style={{ color: 'var(--blue)', fontWeight: 800, fontSize: '13.5px', display: 'inline-flex', alignItems: 'center', gap: 4, textDecoration: 'none', transition: '.2s' }}>
                      Verify A Certificate <ArrowIcon style={{ width: 13, height: 13 }} />
                    </Link>
                  </span>
                </div>
                <div className="kb-row"><span className="kb-label">Research Team Guidance</span><span className="kb-val">Included</span></div>
                <div className="kb-row"><span className="kb-label">Student Support</span><span className="kb-val">Personally Reviewed</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="search-wrap">
        <div className="wrap">
          <div className="search-card">
            <div className="search-card-title">
              <SearchIcon />
              Search All Questions
            </div>
            <div className="search-row">
              <input
                type="search"
                className="search-input"
                id="faqSearch"
                placeholder="Search questions, answers, topics…"
                autoComplete="off"
                aria-label="Search FAQ"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') setQuery('')
                }}
              />
              <button
                type="button"
                className="search-clear"
                id="searchClear"
                aria-label="Clear search"
                style={{ display: normalized ? 'flex' : 'none' }}
                onClick={() => {
                  setQuery('')
                  document.getElementById('faqSearch')?.focus()
                }}
              >
                <Icon strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </Icon>
              </button>
            </div>
            <div className={normalized ? 'search-result-bar visible' : 'search-result-bar'} id="searchResultBar">
              {normalized ? <>Showing <b>{found}</b> of <b>{faqEntries.length}</b> questions</> : null}
            </div>
          </div>
        </div>
      </div>

      <section className="sec" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 48 }} className="reveal">
            <p className="kicker">How It Works</p>
            <h2 className="title">The Research Spectrum Learning Journey</h2>
            <p className="lead" style={{ marginTop: 12 }}>A clear, structured pathway from first enrollment to Research Team eligibility.</p>
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

      <section className="sec rt-highlight-sec">
        <div className="wrap">
          <div className="rth-grid">
            <div className="rth-copy reveal">
              <p className="kicker" style={{ textAlign: 'left' }}>Beyond The Courses</p>
              <h2 className="title" style={{ textAlign: 'left' }}>Research Beyond The Courses</h2>
              <p style={{ color: 'var(--body)', fontSize: 16, lineHeight: 1.7, margin: '14px 0 22px', maxWidth: 520 }}>Finishing your certificates isn&apos;t the end of the journey — it&apos;s the entry point. The Research Team is where Research Spectrum graduates turn training into real, published work.</p>
              <TrustList items={BEYOND} style={{ marginBottom: 24 }} />
              <div className="hero-ctas">
                <Link to="/research-team" className="btn btn-primary">About The Research Team <ArrowIcon /></Link>
                <a href="#cat-research-team" className="btn btn-ghost">Research Team FAQs</a>
              </div>
            </div>
            <div className="reveal" data-d="2">
              <div className="kb-card">
                <div className="kb-title">Research Team At A Glance</div>
                <div className="kb-row"><span className="kb-label">Eligibility</span><span className="kb-val">4 Certificates Required</span></div>
                <div className="kb-row"><span className="kb-label">Selection</span><span className="kb-val">Competitive Application</span></div>
                <div className="kb-row"><span className="kb-label">Project Types</span><span className="kb-val">Reviews, Meta-Analyses &amp; Studies</span></div>
                <div className="kb-row"><span className="kb-label">Collaboration</span><span className="kb-val">Remote, International</span></div>
                <div className="kb-row"><span className="kb-label">Outcome</span><span className="kb-val">Authorship On Published Work</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" style={{ paddingBottom: 56 }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 36 }} className="reveal">
            <p className="kicker">Quick Answers</p>
            <h2 className="title">Popular Questions</h2>
            <p className="lead" style={{ marginTop: 12 }}>Jump straight to the answers students ask about most.</p>
          </div>
          <div className="pop-grid reveal" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            <button className="pop-card" type="button" aria-label="How do I earn a certificate" onClick={() => jumpToQ('q-cert-earn')}>
              <div className="pop-ic"><CertIcon /></div>
              <div className="pop-body"><p>How do I earn a certificate?</p><span>Certificates →</span></div>
            </button>
            <button className="pop-card" type="button" aria-label="What score is required to pass quizzes" onClick={() => jumpToQ('q-quiz-pass')}>
              <div className="pop-ic"><StartedIcon /></div>
              <div className="pop-body"><p>What score is required to pass quizzes?</p><span>Quizzes &amp; Assignments →</span></div>
            </button>
            <button className="pop-card" type="button" aria-label="Do courses include lifetime access" onClick={() => jumpToQ('q-lifetime')}>
              <div className="pop-ic"><ClockIcon /></div>
              <div className="pop-body"><p>Do courses include lifetime access?</p><span>Courses →</span></div>
            </button>
            <button className="pop-card" type="button" aria-label="How does certificate verification work" onClick={() => jumpToQ('q-cert-verify')}>
              <div className="pop-ic"><ShieldIcon strokeWidth="2" /></div>
              <div className="pop-body"><p>How does certificate verification work?</p><span>Certificates →</span></div>
            </button>
            <Link to="/verify" className="btn btn-ghost btn-sm" style={{ marginTop: 10, width: '100%', justifyContent: 'center', borderRadius: 12 }}>
              Verify A Certificate <ArrowIcon style={{ width: 15, height: 15 }} />
            </Link>
          </div>
        </div>
      </section>

      <div className="cat-nav">
        <div className="wrap">
          <div className="cat-nav-inner" id="catNav">
            {SECTIONS.map((section) => {
              const SectionIcon = SECTION_ICONS[section.id]
              return (
                <button
                  key={section.id}
                  className={activeCat === section.id ? 'cat-pill active' : 'cat-pill'}
                  data-cat={section.id}
                  type="button"
                  onClick={() => selectCategory(section.id)}
                >
                  <SectionIcon />
                  {section.title}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div className="wrap">
        <div className={normalized && found === 0 ? 'search-empty show' : 'search-empty'} id="searchEmpty">
          <SearchIcon strokeWidth="1.5" />
          <h3>No results found</h3>
          <p>Try different keywords, or <Link to="/contact" style={linkStyle}>contact support</Link> for help.</p>
        </div>
      </div>

      <div className="wrap" id="faqSections">
        {grouped.map((section) => {
          const visible = section.items.some((item) => itemMatches(item, normalized))
          const SectionIcon = SECTION_ICONS[section.id]
          const className = section.minor ? 'faq-section faq-section-minor' : 'faq-section'
          return (
            <div
              key={section.id}
              className={className}
              id={`cat-${section.id}`}
              style={{
                display: visible ? undefined : 'none',
                ...(section.id === 'support' ? { borderBottom: 'none' } : {}),
              }}
            >
              <div className="faq-sec-head">
                <div className="faq-sec-ic"><SectionIcon /></div>
                <div>
                  <div className="faq-sec-title">
                    {section.title}
                    {section.tag ? <span className="faq-sec-tag">{section.tag}</span> : null}
                  </div>
                  <div className="faq-sec-count">{section.count} questions</div>
                </div>
              </div>
              <div className="rt-faq-list">
                {section.items.map((item) => {
                  const open = openIds.has(item.id)
                  const match = itemMatches(item, normalized)
                  const panelId = `faq-panel-${item.id}`
                  const classNames = [
                    'rt-faq-item',
                    open ? 'open' : '',
                    match ? '' : 'faq-hidden',
                    highlightId === item.id ? 'faq-highlight' : '',
                  ].filter(Boolean).join(' ')
                  return (
                    <div key={item.id} className={classNames} id={item.id} data-q={item.dataQ}>
                      <button
                        className="rt-faq-q"
                        type="button"
                        aria-expanded={open}
                        aria-controls={panelId}
                        onClick={() => toggleItem(item.id)}
                      >
                        <h3>{item.question}</h3>
                        <div className="rt-faq-ic"><PlusIcon /></div>
                      </button>
                      <div className="rt-faq-a" id={panelId}>
                        <p><AnswerParts parts={item.parts} /></p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      <section className="sec" style={{ paddingBottom: 72 }}>
        <div className="wrap">
          <div className="still-help-card reveal">
            <div className="shc-ic"><SupportIcon /></div>
            <div className="shc-body">
              <h3>Still Need Help?</h3>
              <p>If you can&apos;t find what you&apos;re looking for here, reach out and we&apos;ll help. Our team personally reviews every support request and responds within 1–2 business days.</p>
            </div>
            <div className="shc-actions">
              <Link to="/contact" className="btn btn-primary">Contact Support <ArrowIcon /></Link>
              <Link to="/courses#courses-catalog" className="btn btn-ghost">Explore Courses</Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
