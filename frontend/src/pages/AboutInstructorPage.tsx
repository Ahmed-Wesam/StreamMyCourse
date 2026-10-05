import { useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import instructorPhoto from '../assets/prototype/instructor.jpg'
import { listPublishedCourses } from '../lib/api/public-catalog'
import { usePageTitle } from '../lib/page-title'
import './AboutInstructorPage.css'

function useCourseHrefs(): (title: string) => string {
  const [hrefs, setHrefs] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    void listPublishedCourses()
      .then((courses) => {
        if (cancelled) return
        const next: Record<string, string> = {}
        for (const course of courses) {
          next[course.title] = `/courses/${course.id}`
        }
        setHrefs(next)
      })
      .catch(() => {
        /* Static cards stay linked to the catalog when the list is unavailable. */
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (title: string) => hrefs[title] ?? '/courses'
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

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

function ExternalIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15 }}>
      <path d="M7 17 17 7M9 7h8v8" />
    </svg>
  )
}

function OutcomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  )
}

function CheckIcon({ strokeWidth }: { strokeWidth: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

const statValueStyle: CSSProperties = {
  fontSize: 12,
  lineHeight: 1.2,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
}

const pubCardStyle: CSSProperties = {
  display: 'block',
  background: '#fff',
  border: '1px solid var(--line)',
  borderLeft: '4px solid var(--blue)',
  borderRadius: 16,
  padding: '22px 24px',
  boxShadow: 'var(--shadow-sm)',
  transition: '.3s var(--ease)',
  textDecoration: 'none',
}

const pubBadgeStyle: CSSProperties = {
  display: 'inline-block',
  fontSize: 11.5,
  fontWeight: 800,
  letterSpacing: '.04em',
  textTransform: 'uppercase',
  color: 'var(--blue)',
  background: 'var(--sky)',
  padding: '4px 10px',
  borderRadius: 100,
  marginBottom: 12,
  whiteSpace: 'nowrap',
}

const pubTitleStyle: CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: 'var(--ink)',
  lineHeight: 1.45,
}

const talkCardStyle: CSSProperties = {
  background: '#fff',
  border: '1px solid var(--line)',
  borderRadius: 16,
  padding: 24,
  boxShadow: 'var(--shadow-sm)',
}

const viewCourseStyle: CSSProperties = {
  width: '100%',
  justifyContent: 'center',
  marginTop: 4,
}

function FeaturedPublication({ href, badge, title }: { href: string; badge: string; title: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={pubCardStyle}
      onMouseOver={(event) => {
        event.currentTarget.style.transform = 'translateY(-3px)'
        event.currentTarget.style.boxShadow = 'var(--shadow)'
      }}
      onMouseOut={(event) => {
        event.currentTarget.style.transform = ''
        event.currentTarget.style.boxShadow = 'var(--shadow-sm)'
      }}
    >
      <span style={pubBadgeStyle}>{badge}</span>
      <p style={pubTitleStyle}>{title}</p>
    </a>
  )
}

function DoiLink({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--blue)', fontWeight: 600 }}>
      {children}
    </a>
  )
}

const pubItemStyle: CSSProperties = { fontSize: 14.5, color: 'var(--body)', lineHeight: 1.6 }
const authorStyle: CSSProperties = { color: 'var(--ink)' }

const FAQ_ITEMS = [
  {
    q: 'What is your background?',
    a: 'My background is in medical research, with a focus on research methodology, biostatistics, systematic reviews, and scientific writing. I built Research Spectrum after years of teaching research skills to students and observing the same fundamental gaps in research training across institutions and countries. My teaching approach is grounded in practical application — everything I teach, I have personally done in real research projects.',
  },
  {
    q: 'Why did you create Research Spectrum?',
    a: 'I created Research Spectrum because I watched too many capable students and clinicians abandon research not from lack of ability, but from lack of a clear path. Research training is often fragmented — statistics from one source, writing from another, methodology from a third — with no unified curriculum connecting these skills together. Research Spectrum is the structured path I wish had existed when I started.',
  },
  {
    q: 'How did you learn research?',
    a: "The hard way — through years of self-directed trial, error, reading, and mentorship, piecing together a path that no single program offered. That experience is exactly why Research Spectrum is structured the way it is: so students don't have to rebuild that path from scratch the way I did.",
  },
  {
    q: 'Will more courses be added in the future?',
    a: 'Yes. The current four courses form the core research education pathway. Future additions will expand into specialized areas — clinical research design, database research, advanced statistical methods, and research leadership — supporting researchers at every stage, from beginner to advanced practitioner.',
  },
] as const

function AboutFaq() {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  return (
    <div className="ai-faq reveal">
      {FAQ_ITEMS.map((item, index) => (
        <div key={item.q} className={openIndex === index ? 'ai-faq-item open' : 'ai-faq-item'}>
          <button
            type="button"
            className="ai-faq-q"
            onClick={() => setOpenIndex(openIndex === index ? null : index)}
          >
            <h3>{item.q}</h3>
            <div className="ai-faq-ic">
              <PlusIcon />
            </div>
          </button>
          <div className="ai-faq-a">
            <p>{item.a}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

const COURSES: { title: string; delay: string; desc: string; outcome: string; icon: ReactNode }[] = [
  {
    title: 'Research Methodology',
    delay: '1',
    desc: 'Learn how to design rigorous research studies from the ground up — formulating research questions, selecting study designs, and understanding the full research lifecycle.',
    outcome: 'Design and conduct research studies independently',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
        <rect x="9" y="3" width="6" height="4" rx="1" />
      </svg>
    ),
  },
  {
    title: 'Statistics & SPSS',
    delay: '2',
    desc: 'Master the statistical tools used in medical and health research — from descriptive statistics and hypothesis testing to multivariate analysis using SPSS with real datasets.',
    outcome: 'Perform and interpret statistical analyses',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <rect x="7" y="13" width="3" height="5" rx="1" />
        <rect x="12" y="9" width="3" height="9" rx="1" />
        <rect x="17" y="5" width="3" height="13" rx="1" />
      </svg>
    ),
  },
  {
    title: 'Scientific Writing',
    delay: '3',
    desc: 'Write manuscripts that meet the standards of peer-reviewed journals. Learn article structure, academic style, ethical reporting, and how to navigate the submission and revision process.',
    outcome: 'Write and submit publication-ready manuscripts',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
      </svg>
    ),
  },
  {
    title: 'Systematic Reviews & Meta-Analysis',
    delay: '4',
    desc: 'Conduct evidence synthesis at the highest level — designing and executing systematic reviews, performing quantitative meta-analyses, and interpreting pooled effect estimates.',
    outcome: 'Conduct and publish systematic reviews',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    ),
  },
]

const OUTCOMES = [
  'Design and conduct research studies independently',
  'Collect, organize, and prepare research data',
  'Perform statistical analyses using SPSS',
  'Interpret and report statistical results correctly',
  'Write complete, submission-ready manuscripts',
  'Conduct systematic literature reviews',
  'Perform quantitative meta-analyses',
  'Prepare and submit studies for peer-reviewed publication',
  'Collaborate effectively on research projects',
] as const

const PATHWAY = [
  ['Learn', 'Complete the four flagship Research Spectrum courses through structured, practical curriculum.'],
  ['Practice', 'Apply your skills to real datasets, exercises, and research scenarios in each course.'],
  ['Earn Certificates', 'Successfully complete all four courses and earn your verified Research Spectrum certificates.'],
  ['Become Eligible', 'Holding all four certificates makes you eligible to apply for the Research Team.'],
  ['Apply', 'Submit your application and go through a structured selection process based on performance, skills, and fit.'],
  ['Collaborate on Projects', 'Work alongside researchers on active studies — systematic reviews, meta-analyses, and original research.'],
  ['Earn Authorship', 'Through meaningful, documented contributions, earn authorship on peer-reviewed publications.'],
] as const

export default function AboutInstructorPage() {
  usePageTitle('About the Instructor')
  const rootRef = useRef<HTMLDivElement>(null)
  const courseHref = useCourseHrefs()
  useReveal(rootRef)

  return (
    <div ref={rootRef} className="pg-about" data-testid="student-page-about">
      <section className="ai-hero">
        <div className="wrap">
          <div className="ai-hero-grid">
            <div>
              <div className="eyebrow reveal"><span className="dot" />Meet Your Instructor</div>
              <h1 className="reveal" data-d="1">Dr. Bahaa<br /><span className="g">Aburayya</span></h1>
              <p className="sub reveal" data-d="2">Researcher, educator, and founder of Research Spectrum. Dedicated to helping students and healthcare professionals develop the skills needed to conduct, analyze, write, and publish high-quality research independently.</p>
              <div className="ai-hero-ctas reveal" data-d="3">
                <Link to="/courses#courses-catalog" className="btn btn-primary">Explore Courses
                  <ArrowIcon />
                </Link>
                <a href="#story" className="btn btn-ghost">Read My Story</a>
              </div>
            </div>
            <div className="ai-profile-card reveal" data-d="2">
              <div className="ai-avatar">
                <img src={instructorPhoto} alt="Dr. Bahaa Aburayya" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
              </div>
              <div className="ai-name">Dr. Bahaa Aburayya</div>
              <div className="ai-title-line">Researcher &amp; Educator</div>
              <div className="ai-roles">
                <span className="ai-role">Researcher</span>
                <span className="ai-role">Educator</span>
                <span className="ai-role">Founder</span>
              </div>
              <div className="ai-stat-grid">
                <div className="ai-stat"><div className="val">4</div><div className="lbl">Flagship Courses</div></div>
                <div className="ai-stat"><div className="val" style={statValueStyle}>Research Team</div><div className="lbl">Pathway Available</div></div>
                <div className="ai-stat"><div className="val" style={statValueStyle}>End-to-End Curriculum</div><div className="lbl">Full Research Cycle</div></div>
                <div className="ai-stat"><div className="val" style={statValueStyle}>Certificate Per Course</div><div className="lbl">Verified Learning</div></div>
              </div>
              <Link to="/courses#courses-catalog" className="btn btn-primary btn-sm" style={{ width: '100%', justifyContent: 'center' }}>Explore Courses
                <ArrowIcon />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="sec sec-alt" id="profile">
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 40 }}>
            <p className="kicker">Evidence of Expertise</p>
            <h2 className="title">Research Credentials</h2>
            <p>Don&apos;t just take our word for it — verify it. Formal medical training, active research fellowships, and a peer-reviewed publication record you can check for yourself.</p>
          </div>
          <div className="ai-bg-grid">
            <div className="ai-photo-frame reveal">
              <div className="ai-photo-wrap" style={{ padding: 0, justifyContent: 'flex-end' }}>
                <img src={instructorPhoto} alt="Dr. Bahaa Aburayya — Postdoctoral Research Fellow" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 1 }} />
                <div className="ai-photo-label" style={{ position: 'relative', zIndex: 2, width: '100%', margin: 0, padding: '30px 12px 14px', color: '#fff', background: 'linear-gradient(to top,rgba(8,18,41,.82),rgba(8,18,41,.32) 60%,transparent)' }}>Dr. Bahaa Aburayya</div>
              </div>
            </div>
            <div className="reveal" data-d="1">
              <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.02em', marginBottom: 6 }}>Dr. Bahaa Aburayya</p>
              <p style={{ fontSize: 15, color: 'var(--muted)', fontWeight: 600, marginBottom: 18 }}>MD · Researcher · Educator · Founder of Research Spectrum</p>
              <p style={{ fontSize: 15.5, color: 'var(--body)', lineHeight: 1.7, marginBottom: 22 }}>Published researcher with peer-reviewed publications, national and international presentations, and ongoing collaborative research in surgery, clinical outcomes research, systematic reviews, and artificial intelligence in medicine.</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 30 }}>
                <a href="https://pubmed.ncbi.nlm.nih.gov/?term=Aburayya+BI&cauthor_id=36180807" target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm">View PubMed Profile
                  <ExternalIcon />
                </a>
                <a href="https://scholar.google.com/citations?user=-1hFR1wAAAAJ&hl=en&authuser=1" target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">Google Scholar
                  <ExternalIcon />
                </a>
                <a href="https://www.researchgate.net/profile/Bahaa-Aburayya" target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">ResearchGate
                  <ExternalIcon />
                </a>
              </div>
              <div className="ai-cred-list">
                <div className="ai-cred-item">
                  <div className="ai-cred-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z" /><path d="M6 12v5c3 3 9 3 12 0v-5" /></svg></div>
                  <div className="ai-cred-body">
                    <div className="role">Medical Doctor</div>
                    <div className="org">Jordan University of Science and Technology</div>
                    <div className="detail">Faculty of Medicine — Doctor of Medicine (MD)</div>
                  </div>
                </div>
                <div className="ai-cred-item">
                  <div className="ai-cred-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg></div>
                  <div className="ai-cred-body">
                    <div className="role">Postdoctoral Research Fellow</div>
                    <div className="org">Mayo Clinic, Arizona</div>
                    <div className="detail">Department of Surgery — Division of Cardiothoracic Surgery</div>
                  </div>
                </div>
                <div className="ai-cred-item">
                  <div className="ai-cred-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 21h18" /><path d="M5 21V7l7-4 7 4v14" /><path d="M9 9h.01M12 9h.01M15 9h.01M9 13h.01M12 13h.01M15 13h.01" /></svg></div>
                  <div className="ai-cred-body">
                    <div className="role">Remote Research Collaborator</div>
                    <div className="org">University of California, San Francisco (UCSF)</div>
                    <div className="detail">Department of Surgery — Division of Surgical Oncology</div>
                  </div>
                </div>
                <div className="ai-cred-item">
                  <div className="ai-cred-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" /></svg></div>
                  <div className="ai-cred-body">
                    <div className="role">Published Researcher</div>
                    <div className="org">Peer-Reviewed Medical Research</div>
                    <div className="detail">General surgery, systematic reviews, and clinical outcomes research</div>
                  </div>
                </div>
                <div className="ai-cred-item">
                  <div className="ai-cred-ic" style={{ background: '#dcf5e3', borderColor: '#bce7c8', color: '#0d6f3e' }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><path d="m7 14 3-3 3 2 4-5" /></svg></div>
                  <div className="ai-cred-body">
                    <div className="role">Founder, Research Spectrum</div>
                    <div className="org">Research Education Platform</div>
                    <div className="detail">Structured, end-to-end research education for healthcare professionals worldwide</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" id="publications">
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 40 }}>
            <p className="kicker">Peer-Reviewed Research</p>
            <h2 className="title">Featured Publications</h2>
            <p>A selection of peer-reviewed work in surgery, systematic reviews, and clinical outcomes research. Every entry is verifiable through the linked profiles above.</p>
          </div>
          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(270px,1fr))', gap: 18 }}>
            <FeaturedPublication href="https://doi.org/10.3390/cancers17183015" badge="Cancers · 2025" title="Minimally invasive distal pancreatectomy as the standard of care in the US: are we there yet?" />
            <FeaturedPublication href="https://doi.org/10.1007/s13304-024-02029-5" badge="Updates in Surgery · 2024" title="Critical view of safety approach vs. infundibular technique in laparoscopic cholecystectomy" />
            <FeaturedPublication href="https://doi.org/10.1007/s10143-022-01873-6" badge="Neurosurgical Review · 2022" title="Risk of meningitis after posterior fossa decompression with duraplasty using different graft types" />
            <FeaturedPublication href="https://doi.org/10.1016/j.ijscr.2024.109265" badge="Int. J. Surg. Case Rep. · 2024" title="Complete Common Bile Duct Injury after Laparoscopic Cholecystectomy in Situs Inversus Totalis" />
          </div>

          <details className="reveal" style={{ marginTop: 28, background: '#fff', border: '1px solid var(--line)', borderRadius: 16, boxShadow: 'var(--shadow-sm)' }}>
            <summary style={{ listStyle: 'none', cursor: 'pointer', padding: '18px 24px', fontWeight: 800, fontSize: 15.5, color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
              <span>View Full Publication List</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ width: 18, height: 18, flex: 'none' }}><path d="m6 9 6 6 6-6" /></svg>
            </summary>
            <div style={{ padding: '4px 26px 26px' }}>
              <p style={{ fontSize: 12, fontWeight: 800, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--muted)', margin: '6px 0 14px' }}>Peer-Reviewed Publications</p>
              <ol style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <li style={pubItemStyle}>Foroutani L, Gonzalez A, Wang JJ, <strong style={authorStyle}>Aburayya BI</strong>, Ganjouei AA, Feng J, Thornblade LW, Hirose K, Maker AV, Nakakura E, Corvera CU, Alseidi A, Adam MA. Minimally invasive distal pancreatectomy as the standard of care in the US: are we there yet? <em>Cancers.</em> 2025;17(18):3015. <DoiLink href="https://doi.org/10.3390/cancers17183015">doi:10.3390/cancers17183015</DoiLink></li>
                <li style={pubItemStyle}>Mansour S, <strong style={authorStyle}>Aburayya BI</strong>, Al Ramadneh J, Shakhatreh Z, Alsmadi AS, Ali AA, Shahait AD. A global registry-based analysis of clinical trials on robotic-assisted inguinal hernia repair: current landscape and research gaps. <em>J Robot Surg.</em> 2025 Aug 4;19(1):447. <DoiLink href="https://doi.org/10.1007/s11701-025-02614-9">doi:10.1007/s11701-025-02614-9</DoiLink></li>
                <li style={pubItemStyle}>Foroutani L, Ashraf Ganjouei A, Wang JJ, <strong style={authorStyle}>Aburayya BI</strong>, Corvera C, Alseidi A, Adam MA. ASO Author Reflections: Innovative Robot-Assisted Endoluminal Resection for Gastroesophageal Junction Leiomyomas. <em>Ann Surg Oncol.</em> 2025 Feb;32(2):1251-1252. <DoiLink href="https://doi.org/10.1245/s10434-024-16613-x">doi:10.1245/s10434-024-16613-x</DoiLink></li>
                <li style={pubItemStyle}>Foroutani L, Ashraf Ganjouei A, Wang J, <strong style={authorStyle}>Aburayya BI</strong>, Corvera C, Alseidi A, Adam MA. Robotic-Assisted Endoluminal Resection of Gastroesophageal Junction Leiomyoma with Transoral Specimen Extraction: Technique, Outcome, and Safety. <em>Ann Surg Oncol.</em> 2025 Feb;32(2):1218-1219. <DoiLink href="https://doi.org/10.1245/s10434-024-16426-y">doi:10.1245/s10434-024-16426-y</DoiLink></li>
                <li style={pubItemStyle}><strong style={authorStyle}>Aburayya BI</strong>, Al-Hayk AK, Toubasi AA, Ali A, Shahait AD. Critical view of safety approach vs. infundibular technique in laparoscopic cholecystectomy, which one is safer? A systematic review and meta-analysis. <em>Updates Surg.</em> 2024 Nov 11. <DoiLink href="https://doi.org/10.1007/s13304-024-02029-5">doi:10.1007/s13304-024-02029-5</DoiLink></li>
                <li style={pubItemStyle}><strong style={authorStyle}>Aburayya BI</strong>, Obeidat LR, Kitana FI, Al Khatib O, Romman S, Hamed OH. Complete Common Bile Duct Injury after Laparoscopic Cholecystectomy in Situs Inversus Totalis: A Case Report, Review of the Literature and Illustrative Case Video. <em>Int J Surg Case Rep.</em> 2024 Feb;115:109265. <DoiLink href="https://doi.org/10.1016/j.ijscr.2024.109265">doi:10.1016/j.ijscr.2024.109265</DoiLink></li>
                <li style={pubItemStyle}>Jbarah OF, <strong style={authorStyle}>Aburayya BI</strong>, Shatnawi AR, Alkhasoneh MA, Toubasi AA, Alharahsheh SM, Nukho SK, Nassar AS, Jamous MA. Risk of meningitis after posterior fossa decompression with duraplasty using different graft types in patients with Chiari malformation type I and syringomyelia: a systematic review and meta-analysis. <em>Neurosurg Rev.</em> 2022 Dec;45(6):3537-3550. <DoiLink href="https://doi.org/10.1007/s10143-022-01873-6">doi:10.1007/s10143-022-01873-6</DoiLink></li>
              </ol>
            </div>
          </details>
        </div>
      </section>

      <section className="sec sec-alt" id="presentations">
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: 40 }}>
            <p className="kicker">Academic Engagement</p>
            <h2 className="title">Presentation Highlights</h2>
            <p>Selected podium and poster presentations at national and international surgical meetings — evidence of active participation in the research community.</p>
          </div>
          <div className="reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 18 }}>
            <div style={talkCardStyle}>
              <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--blue)', letterSpacing: '.04em' }}>2025</div>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink)', margin: '6px 0 6px', letterSpacing: '-.01em' }}>SSO ACT Meeting</div>
              <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.5 }}>Society of Surgical Oncology — Scottsdale, AZ</div>
            </div>
            <div style={talkCardStyle}>
              <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--blue)', letterSpacing: '.04em' }}>2025</div>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink)', margin: '6px 0 6px', letterSpacing: '-.01em' }}>NCC-ACS Annual Meeting</div>
              <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.5 }}>Northern California Chapter, American College of Surgeons</div>
            </div>
            <div style={talkCardStyle}>
              <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--blue)', letterSpacing: '.04em' }}>2025</div>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink)', margin: '6px 0 6px', letterSpacing: '-.01em' }}>EAES Congress</div>
              <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.5 }}>33rd International EAES Congress — Belgrade, Serbia</div>
            </div>
            <div style={talkCardStyle}>
              <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--blue)', letterSpacing: '.04em' }}>2024</div>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink)', margin: '6px 0 6px', letterSpacing: '-.01em' }}>SAGES Annual Meeting</div>
              <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.5 }}>Society of American Gastrointestinal and Endoscopic Surgeons — Cleveland, OH</div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" id="story">
        <div className="wrap">
          <div className="ai-story-grid">
            <div className="reveal">
              <h2>Why I Created<br /><span className="g" style={{ background: 'var(--grad-cta)', WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}>Research Spectrum</span></h2>
              <p style={{ marginTop: 20 }}>Research training is often fragmented. Students are expected to learn statistics from one source, scientific writing from another, and systematic reviews from somewhere else entirely — with no single path that connects these skills into a cohesive, publishable research capability.</p>
              <p>Many talented clinicians and students abandon research not because they lack the intellectual ability, but because they lack structured guidance. I watched this happen repeatedly — colleagues with genuine curiosity and valuable clinical observations who had no framework for converting those observations into publishable work.</p>
              <div className="ai-pull-quote">
                <p>&quot;I also lived through this confusion myself. My own research education was self-directed, scattered, and inefficient. The skills I eventually developed came from years of trial, error, reading, and mentorship — a path that was far harder than it needed to be.&quot;</p>
              </div>
              <p>Research Spectrum is my answer to that problem — built so the next person doesn&apos;t have to find their own way through the confusion the way I did.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="sec sec-alt">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">The Curriculum</p>
            <h2 className="title">Courses I Teach</h2>
            <p>Four flagship courses covering the complete research lifecycle — from study design to peer-reviewed publication.</p>
          </div>
          <div className="ai-course-grid">
            {COURSES.map((course) => (
              <div key={course.title} className="ai-cc reveal" data-d={course.delay}>
                <div className="ai-cc-top">
                  <div className="ai-cc-icon">{course.icon}</div>
                  <span className="ai-cert-pill"><CheckIcon strokeWidth="2.6" />Certificate Available</span>
                </div>
                <h3>{course.title}</h3>
                <p className="desc">{course.desc}</p>
                <p className="outcome"><OutcomeIcon />{course.outcome}</p>
                <Link to={courseHref(course.title)} className="btn btn-ghost btn-sm" style={viewCourseStyle}>View Course
                  <ArrowIcon />
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sec" id="difference">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">The Difference</p>
            <h2 className="title">What Makes Research Spectrum Different</h2>
            <p>Most research education teaches you about research — Research Spectrum teaches you to do it.</p>
          </div>
          <div className="ai-diff-wrap">
            <div className="ai-cards-3 reveal" data-d="1">
              <div className="ai-card">
                <div className="ai-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg></div>
                <h3>Four Connected Courses</h3>
                <p>A single curriculum that covers the full research cycle — methodology, statistics, writing, and systematic reviews — built to work together, not as standalone topics.</p>
              </div>
              <div className="ai-card">
                <div className="ai-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><rect x="7" y="13" width="3" height="5" rx="1" /><rect x="12" y="9" width="3" height="9" rx="1" /><rect x="17" y="5" width="3" height="13" rx="1" /></svg></div>
                <h3>Real Datasets, Real Practice</h3>
                <p>Every concept is reinforced with authentic datasets and research scenarios, so skills are built through application rather than abstract theory.</p>
              </div>
              <div className="ai-card">
                <div className="ai-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg></div>
                <h3>Competency-Based Learning</h3>
                <p>Progress is measured by what you can actually do — design a study, run an analysis, write a manuscript — not just by lessons completed.</p>
              </div>
              <div className="ai-card">
                <div className="ai-ic" style={{ background: '#dcf5e3', borderColor: '#bce7c8', color: '#0d6f3e' }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg></div>
                <h3>Research Team Pathway</h3>
                <p>Graduates of all four courses become eligible to apply for the Research Team and continue their development beyond the curriculum.</p>
              </div>
              <div className="ai-card">
                <div className="ai-ic" style={{ background: '#fff5d6', borderColor: '#f3df9a', color: '#a96b00' }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg></div>
                <h3>Authorship Opportunities</h3>
                <p>Research Team members contribute to active studies and can earn authorship on peer-reviewed publications through meaningful, documented work.</p>
              </div>
              <div className="ai-card">
                <div className="ai-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" /></svg></div>
                <h3>Publication-Oriented Training</h3>
                <p>From the first lesson, every course is oriented toward one outcome: a publication-ready research capability you can use independently.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec sec-alt">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Is This For You?</p>
            <h2 className="title">Who Research Spectrum Is For</h2>
            <p>If you see yourself here, these courses were built for you.</p>
          </div>
          <div className="ai-who-grid">
            <div className="ai-who-card reveal" data-d="1">
              <span className="ai-who-emo">🎓</span>
              <h3>Medical Students</h3>
              <p>Building your research skills early — before residency, before fellowship, and before the pressure begins.</p>
            </div>
            <div className="ai-who-card reveal" data-d="2">
              <span className="ai-who-emo">🏥</span>
              <h3>Residents &amp; Fellows</h3>
              <p>Time-limited and training-focused — you need practical, efficient research skills that fit your schedule.</p>
            </div>
            <div className="ai-who-card reveal" data-d="3">
              <span className="ai-who-emo">👨‍⚕️</span>
              <h3>Physicians &amp; Clinicians</h3>
              <p>You have clinical observations and questions — you just need the tools to turn them into publishable research.</p>
            </div>
            <div className="ai-who-card reveal" data-d="1">
              <span className="ai-who-emo">💊</span>
              <h3>Nurses &amp; Allied Health</h3>
              <p>Research literacy and publication skills are increasingly important across all healthcare roles, not just physicians.</p>
            </div>
            <div className="ai-who-card reveal" data-d="2">
              <span className="ai-who-emo">🔬</span>
              <h3>Early-Career Researchers</h3>
              <p>Stepping into research without a mentor or structured program — you need a clear, self-directed learning path.</p>
            </div>
            <div className="ai-who-card reveal" data-d="3">
              <span className="ai-who-emo">🎯</span>
              <h3>Aspiring Academic Researchers</h3>
              <p>Working toward a career built on publications and academic standing — you need a reliable system for producing research consistently.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="sec">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Approach to Teaching</p>
            <h2 className="title">My Teaching Philosophy</h2>
            <p>Two ideas run through everything: research skills must be <em>practical</em>, and every student should become an <em>independent</em> researcher.</p>
          </div>
          <div className="ai-cards-3" style={{ gridTemplateColumns: 'repeat(2,1fr)', maxWidth: 820, margin: '0 auto' }}>
            <div className="ai-card reveal" data-d="1">
              <div className="ai-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg></div>
              <h3>Practical Over Theoretical</h3>
              <p>Concepts are taught through application, not abstraction — real datasets, authentic scenarios, and lessons that build transferable skills rather than tool-specific procedures.</p>
            </div>
            <div className="ai-card reveal" data-d="2">
              <div className="ai-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg></div>
              <h3>Building Independent Researchers</h3>
              <p>The goal is a capable, self-sufficient researcher who can design, execute, analyze, write, and publish — with every course working toward that publication-ready outcome.</p>
            </div>
            <div className="ai-card reveal" data-d="1">
              <div className="ai-ic" style={{ background: '#dcf5e3', borderColor: '#bce7c8', color: '#0d6f3e' }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg></div>
              <h3>Integrity &amp; Rigor</h3>
              <p>Honest representation of research and methodological soundness are non-negotiable — students learn not just how to do research, but how to do it correctly and transparently.</p>
            </div>
            <div className="ai-card reveal" data-d="2">
              <div className="ai-ic" style={{ background: '#fff5d6', borderColor: '#f3df9a', color: '#a96b00' }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="6" /><path d="M9 13.8 7 22l5-3 5 3-2-8.2" /></svg></div>
              <h3>Quality &amp; Continuous Growth</h3>
              <p>No shortcuts in education or research — and the curriculum keeps evolving to reflect current methodological standards and best practices.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="sec">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Graduate Capabilities</p>
            <h2 className="title">What Students Will Be Able To Do</h2>
            <p>After completing the full Research Spectrum pathway, students develop a complete, independent research capability — ready to design, execute, analyze, write, and publish original research.</p>
          </div>
          <div className="able-grid">
            {OUTCOMES.map((label, index) => (
              <div key={label} className="able reveal" data-d={String((index % 4) + 1)}>
                <div className="ck"><CheckIcon strokeWidth="2.5" /></div>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sec sec-alt">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">The Full Ecosystem</p>
            <h2 className="title">Beyond Courses</h2>
            <p>Completing the four-course curriculum is the foundation — and for those who want to go further, it opens the door to the next stage of the research journey.</p>
          </div>
          <div className="ai-rt-grid" style={{ display: 'grid', gridTemplateColumns: '1fr .9fr', gap: 64, alignItems: 'center' }}>
            <div className="ai-pathway reveal">
              {PATHWAY.map(([title, body], index) => (
                <div key={title} className="ai-pitem">
                  <div className="ai-pnum">{index + 1}</div>
                  <div className="ai-ptext"><h4>{title}</h4><p>{body}</p></div>
                </div>
              ))}
            </div>
            <div className="reveal" data-d="1">
              <div style={{ background: 'var(--grad)', borderRadius: 24, padding: 36, boxShadow: 'var(--shadow-lg)', color: '#fff', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', inset: 0, backgroundImage: 'radial-gradient(rgba(255,255,255,.07) 1px,transparent 1px)', backgroundSize: '24px 24px' }} />
                <div style={{ position: 'relative' }}>
                  <p style={{ fontSize: 11.5, fontWeight: 800, letterSpacing: '.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,.65)', marginBottom: 12 }}>Research Spectrum</p>
                  <h3 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-.02em', marginBottom: 14, lineHeight: 1.15 }}>From Learning To Publishing</h3>
                  <p style={{ fontSize: 15, color: 'rgba(255,255,255,.82)', lineHeight: 1.65, marginBottom: 24 }}>The ultimate goal of Research Spectrum isn&apos;t simply course completion — it&apos;s helping learners develop the skills to design studies, analyze data, write scientific manuscripts, and contribute to meaningful research. For students who continue beyond the curriculum, the pathway extends further still — toward real research participation, collaboration with other researchers, and publishable scientific work.</p>
                  <Link to="/courses#courses-catalog" className="btn btn-white" style={{ width: '100%', justifyContent: 'center' }}>Explore Courses
                    <ArrowIcon />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" id="faq">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Frequently Asked Questions</p>
            <h2 className="title">Common Questions</h2>
          </div>
          <AboutFaq />
          <p className="reveal" style={{ textAlign: 'center', marginTop: 32 }}>
            <Link to="/faq" className="btn btn-ghost">View Full FAQ
              <ArrowIcon />
            </Link>
          </p>
        </div>
      </section>

      <section className="sec" style={{ paddingBottom: 100 }}>
        <div className="wrap">
          <div className="ai-cta reveal">
            <p className="kicker" style={{ color: 'rgba(255,255,255,.72)', marginBottom: 16 }}>Begin Your Journey</p>
            <h2>Start Your Research Journey</h2>
            <p>Whether you&apos;re taking your first steps into research or looking to strengthen your existing skills, Research Spectrum is designed to help you build practical, publication-ready research capabilities.</p>
            <div className="btn-row">
              <Link to="/courses#courses-catalog" className="btn btn-white">Explore Courses
                <ArrowIcon />
              </Link>
              <a href="#profile" className="btn" style={{ background: 'rgba(255,255,255,.14)', color: '#fff', border: '1.5px solid rgba(255,255,255,.22)' }}>Meet The Instructor</a>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
