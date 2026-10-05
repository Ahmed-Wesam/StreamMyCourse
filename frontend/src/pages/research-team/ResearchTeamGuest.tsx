import { useState, type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { ArrowIcon, CheckIcon, PlusIcon, RtIcon } from './rtIcon'

const pathway = [
  { kind: 'course' as const, label: 'Research Methodology' },
  { kind: 'course' as const, label: 'Statistics & SPSS' },
  { kind: 'course' as const, label: 'Scientific Writing' },
  { kind: 'course' as const, label: 'Systematic Reviews & Meta-Analysis' },
  { kind: 'cert' as const, label: 'Earn all four certificates' },
  { kind: 'goal' as const, label: 'Become eligible to apply' },
]

function PathwayIcon({ kind }: { kind: (typeof pathway)[number]['kind'] }) {
  if (kind === 'cert') {
    return (
      <RtIcon strokeWidth="2.4">
        <circle cx="12" cy="8" r="6" />
        <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
      </RtIcon>
    )
  }
  if (kind === 'goal') {
    return (
      <RtIcon strokeWidth="2.5">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </RtIcon>
    )
  }
  return <CheckIcon />
}

function GuestPathway({ style }: { style?: CSSProperties }) {
  return (
    <div className="rt-guest-pathway" style={style}>
      {pathway.map((step) => (
        <div className="rt-guest-step" key={step.label}>
          <span className={`rt-guest-step-dot ${step.kind}`}>
            <PathwayIcon kind={step.kind} />
          </span>
          <span className={step.kind === 'goal' ? 'rt-guest-step-label goal' : 'rt-guest-step-label'}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  )
}

function GuestHero() {
  return (
    <section className="rt-hero">
      <div className="wrap">
        <div className="rt-hero-grid">
          <div>
            <div className="eyebrow reveal"><span className="dot"></span>Research Spectrum Program</div>
            <h1 className="reveal" data-d="1" id="rt-hero-h1">The <span className="g">Research Team</span><br />Real Projects. Real Publications.</h1>
            <p className="sub reveal" data-d="2" id="rt-hero-sub">
              Join a community of researchers turning coursework into published evidence. Research
              Team members co-author systematic reviews, meta-analyses, and original studies —
              with mentorship from experienced researchers every step of the way.
            </p>
            <div className="rt-hero-ctas reveal" data-d="3">
              <Link to="/courses" className="btn btn-primary" id="rt-hero-cta">
                <span id="rt-hero-cta-text">Explore Courses</span>
                <ArrowIcon />
              </Link>
              <Link to="/register" className="btn btn-ghost" id="rt-hero-secondary-link">
                <span id="rt-hero-secondary-link-text">Create Account</span>
              </Link>
            </div>
            <div className="rt-personal-strip reveal" data-d="4" id="rt-personal-strip">
              <RtIcon strokeWidth="2.2">
                <circle cx="12" cy="8" r="5" />
                <path d="M20 21a8 8 0 0 0-16 0" />
              </RtIcon>
              <span id="rt-personal-msg">
                Create a free account and complete all four Research Spectrum courses to unlock the
                Research Team application.
              </span>
            </div>
          </div>
          <div className="rt-hero-card rt-guest-only reveal" data-d="2">
            <h3>Research Team Eligibility</h3>
            <p style={{ fontSize: 14, color: 'var(--body)', lineHeight: 1.6, marginBottom: 20 }}>
              Create an account and complete all four Research Spectrum courses to become eligible
              to apply to the Research Team.
            </p>
            <GuestPathway style={{ marginBottom: 20 }} />
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Link
                to="/courses"
                className="btn btn-primary btn-sm"
                style={{ flex: 1, justifyContent: 'center' }}
              >
                Explore Courses
              </Link>
              <Link
                to="/register"
                className="btn btn-ghost btn-sm"
                style={{ flex: 1, justifyContent: 'center' }}
              >
                Create Account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

const whyCards: Array<{ title: string; body: string; delay: string; icon: ReactNode }> = [
  {
    title: 'Real Research Experience',
    body: 'Move beyond theory and apply your skills to active, ongoing research projects alongside experienced researchers.',
    delay: '1',
    icon: (
      <RtIcon>
        <path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
        <path d="M2 21a7 7 0 0 1 14 0" />
        <path d="M19 8v6M16 11h6" />
      </RtIcon>
    ),
  },
  {
    title: 'Publication Opportunities',
    body: 'Contribute to manuscripts prepared for submission to peer-reviewed journals as part of an active research pipeline.',
    delay: '2',
    icon: (
      <RtIcon>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6M9 15l2 2 4-4" />
      </RtIcon>
    ),
  },
  {
    title: 'Authorship Opportunities',
    body: 'Earn co-authorship on published work based on the level and quality of your contribution to each project.',
    delay: '3',
    icon: (
      <RtIcon>
        <circle cx="12" cy="8" r="6" />
        <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
      </RtIcon>
    ),
  },
  {
    title: 'Expert Mentorship',
    body: 'Work directly with the Research Spectrum instructor team, with feedback and guidance on every stage of a project.',
    delay: '1',
    icon: (
      <RtIcon>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="m17 11 2 2 4-4" />
      </RtIcon>
    ),
  },
  {
    title: 'Advanced Research Skills',
    body: 'Sharpen advanced statistical analysis, data extraction, and manuscript-writing skills on real datasets.',
    delay: '2',
    icon: (
      <RtIcon>
        <path d="M3 3v18h18" />
        <rect x="7" y="13" width="3" height="5" rx="1" />
        <rect x="12" y="9" width="3" height="9" rx="1" />
        <rect x="17" y="5" width="3" height="13" rx="1" />
      </RtIcon>
    ),
  },
  {
    title: 'Professional Network',
    body: 'Connect with a growing community of researchers, clinicians, and collaborators across the platform.',
    delay: '3',
    icon: (
      <RtIcon>
        <circle cx="9" cy="7" r="4" />
        <path d="M2 21a7 7 0 0 1 14 0" />
        <circle cx="17" cy="7" r="3" />
        <path d="M23 21a6 6 0 0 0-5-5.9" />
      </RtIcon>
    ),
  },
]

function WhyJoinSection() {
  return (
    <section className="sec sec-feature" id="why-join">
      <div className="wrap">
        <div className="sec-head sec-head-lg">
          <span className="kicker reveal">Why It Matters</span>
          <h2 className="title reveal" data-d="1">
            Why Join The Research Team
          </h2>
          <p className="lead reveal" data-d="2">
            This is where your training becomes real research output — experience, mentorship, and
            recognition you can carry into the rest of your career.
          </p>
        </div>
        <div className="rt-cards-3" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
          {whyCards.map((card) => (
            <div className="rt-card reveal" data-d={card.delay} key={card.title}>
              <div className="rc-icon">{card.icon}</div>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const projectCards: Array<{
  title: string
  body: string
  tags: string[]
  delay: string
  icon: ReactNode
}> = [
  {
    title: 'Systematic Reviews',
    body: 'Search, screen, and synthesize the existing literature on a focused clinical question.',
    tags: ['Literature Search', 'Screening'],
    delay: '1',
    icon: (
      <RtIcon>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
      </RtIcon>
    ),
  },
  {
    title: 'Meta-Analyses',
    body: 'Pool data across studies and run statistical analyses to estimate combined effect sizes.',
    tags: ['Statistics', 'Forest Plots'],
    delay: '2',
    icon: (
      <RtIcon>
        <path d="M3 3v18h18" />
        <circle cx="8" cy="14" r="2" />
        <circle cx="13" cy="9" r="2" />
        <circle cx="18" cy="13" r="2" />
        <path d="M9.5 12.7 11.3 10.3M14.7 9.9 16.3 11.7" />
      </RtIcon>
    ),
  },
  {
    title: 'Cross-Sectional Studies',
    body: 'Design and analyze studies that capture a population at a single point in time.',
    tags: ['Survey Design', 'SPSS'],
    delay: '3',
    icon: (
      <RtIcon>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M3 9h18M9 21V9" />
      </RtIcon>
    ),
  },
  {
    title: 'Database Research',
    body: 'Work with large clinical and public health databases to answer population-level questions.',
    tags: ['Data Extraction', 'Cleaning'],
    delay: '1',
    icon: (
      <RtIcon>
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </RtIcon>
    ),
  },
  {
    title: 'Retrospective Studies',
    body: 'Analyze existing patient records and outcomes to identify meaningful clinical patterns.',
    tags: ['Chart Review', 'Outcomes'],
    delay: '2',
    icon: (
      <RtIcon>
        <path d="M12 8v4l3 3" />
        <circle cx="12" cy="12" r="9" />
      </RtIcon>
    ),
  },
  {
    title: 'Literature Reviews',
    body: 'Summarize and contextualize current evidence to support new research questions.',
    tags: ['Writing', 'Synthesis'],
    delay: '3',
    icon: (
      <RtIcon>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
        <path d="M9 7h6M9 11h6M9 15h3" />
      </RtIcon>
    ),
  },
]

function ProjectsSection() {
  return (
    <section className="sec" id="projects">
      <div className="wrap">
        <div className="sec-head sec-head-lg">
          <span className="kicker reveal">What You&apos;ll Work On</span>
          <h2 className="title reveal" data-d="1">
            Research Projects
          </h2>
          <p className="lead reveal" data-d="2">
            Research Team members rotate through a wide range of project types — giving you breadth
            across study designs and methods.
          </p>
        </div>
        <div className="rt-cards-3">
          {projectCards.map((card) => (
            <div className="rt-proj-card reveal" data-d={card.delay} key={card.title}>
              <div className="rc-icon">{card.icon}</div>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
              <div className="rt-tags">
                {card.tags.map((tag) => (
                  <span className="rt-tag" key={tag}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const contributions = [
  'Literature Searching & Screening',
  'Data Extraction & Quality Assessment',
  'Statistical Analysis',
  'Manuscript Writing & Revision',
  'Critical Review & Feedback',
  'Project Coordination',
]

function AuthorshipSection() {
  return (
    <section className="sec">
      <div className="wrap">
        <div className="sec-head">
          <span className="kicker reveal">Authorship</span>
          <h2 className="title reveal" data-d="1">
            Earn Authorship Through Meaningful Contribution
          </h2>
          <p className="lead reveal" data-d="2">
            Research Team members have the opportunity to earn authorship on published research
            through substantive scientific contributions.
          </p>
        </div>
        <div className="rt-authorship reveal">
          <div className="rt-auth-block-h">
            <div className="rc-icon">
              <RtIcon>
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </RtIcon>
            </div>
            <h3 className="rt-auth-list-h" style={{ marginBottom: 0 }}>
              Contributions May Include
            </h3>
          </div>
          <div className="rt-auth-contrib-grid">
            {contributions.map((item) => (
              <div className="rt-auth-contrib" key={item}>
                <span className="lc">
                  <CheckIcon strokeWidth="2.4" />
                </span>
                {item}
              </div>
            ))}
          </div>
          <div className="rt-auth-growth">
            <h4>
              <RtIcon strokeWidth="2" style={{ width: 17, height: 17, color: 'var(--blue)' }}>
                <path d="M3 3v18h18" />
                <path d="m19 9-5 5-4-4-3 3" />
              </RtIcon>
              Growth Path
            </h4>
            <p>
              As your skills and involvement grow, so can your role within a project — from
              contributor to lead collaborator. Authorship decisions are based on meaningful
              scientific contribution and follow recognised academic standards.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

const steps = [
  {
    n: '1',
    title: 'Learn',
    body: 'Complete the four Research Spectrum courses and earn your certificates.',
  },
  {
    n: '2',
    title: 'Apply',
    body: "Submit your Research Team application once you're eligible.",
  },
  {
    n: '3',
    title: 'Join Projects',
    body: 'Get matched to active research projects based on your interests.',
  },
  {
    n: '4',
    title: 'Publish',
    body: 'Contribute toward manuscripts and earn authorship on published work.',
  },
]

function HowItWorksSection() {
  return (
    <section className="sec">
      <div className="wrap">
        <div className="sec-head">
          <span className="kicker reveal">The Path</span>
          <h2 className="title reveal" data-d="1">
            How It Works
          </h2>
          <p className="lead reveal" data-d="2">
            From your first course to your first publication.
          </p>
        </div>
        <div className="rt-steps-wrap">
          <div className="rt-steps-connector" />
          <div className="rt-steps">
            {steps.map((step) => (
              <div className="rt-step reveal" data-d={step.n} key={step.n}>
                <div className="rt-step-num">{step.n}</div>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function GuestApplicationSection({ error }: { error: string | null }) {
  return (
    <section className="sec sec-tight" id="application-status">
      <div className="wrap">
        <div className="sec-head rt-guest-only">
          <span className="kicker reveal">Before You Apply</span>
          <h2 className="title reveal" data-d="1">
            Research Team Applications Require Eligibility
          </h2>
          <p className="lead reveal" data-d="2">
            To apply, learners must complete all four Research Spectrum courses and earn all four
            certificates.
          </p>
          {error ? (
            <p className="lead" style={{ color: '#b91c1c' }}>
              {error}
            </p>
          ) : null}
        </div>
        <div
          className="rt-app-card rt-guest-only reveal"
          style={{ alignItems: 'center', textAlign: 'left', gap: 22, padding: '36px 40px' }}
        >
          <GuestPathway style={{ maxWidth: 380, width: '100%', margin: '0 auto' }} />
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center', width: '100%' }}>
            <Link to="/courses" className="btn btn-primary">
              Explore Courses
              <ArrowIcon />
            </Link>
            <Link to="/register" className="btn btn-ghost">
              Create Account
            </Link>
          </div>
          <p style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, textAlign: 'center', margin: 0 }}>
            Eligibility does not guarantee acceptance. Selection considers interviews, course
            performance, assignments, English proficiency, and research skills.
          </p>
        </div>
      </div>
    </section>
  )
}

const faqs = [
  {
    q: 'Who can apply to the Research Team?',
    a: 'Any student who has completed all four Research Spectrum courses — Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis — and earned their certificates is eligible to apply.',
  },
  {
    q: 'Does eligibility guarantee acceptance?',
    a: 'No. Eligibility means you may submit an application. Selection is based on interviews, course performance, assignment quality, English proficiency, and overall research skills.',
  },
  {
    q: 'How long does the review process take?',
    a: 'Applications are reviewed on a rolling basis, typically within 2–4 weeks. Your status on this page updates automatically as your application progresses.',
  },
  {
    q: 'How is authorship decided?',
    a: 'Authorship reflects the level of meaningful contribution to a project — including literature work, data analysis, writing, and revisions. Roles grow as you gain experience on the team.',
  },
  {
    q: "What if I'm not selected?",
    a: "Not all applicants are selected in a given cycle. You're encouraged to continue building your skills and re-apply in a future cycle.",
  },
]

export function FaqSection() {
  const [open, setOpen] = useState<number | null>(null)

  return (
    <section className="sec sec-tight">
      <div className="wrap">
        <div className="sec-head">
          <span className="kicker reveal">FAQ</span>
          <h2 className="title reveal" data-d="1">
            Frequently Asked Questions
          </h2>
          <p className="lead reveal" data-d="2">
            Common questions about the Research Team.
          </p>
        </div>
        <div className="rt-faq-list reveal">
          {faqs.map((item, index) => {
            const isOpen = open === index
            return (
              <div className={isOpen ? 'rt-faq-item open' : 'rt-faq-item'} key={item.q}>
                <button
                  className="rt-faq-q"
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => setOpen(isOpen ? null : index)}
                >
                  <h3>{item.q}</h3>
                  <div className="rt-faq-ic">
                    <PlusIcon />
                  </div>
                </button>
                <div className="rt-faq-a">
                  <p>{item.a}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export function FinalCtaSection({ canSubmit = false }: { canSubmit?: boolean }) {
  return (
    <section className="sec">
      <div className="wrap">
        <div className="rt-final-cta reveal">
          <span className="kicker-w">Your Next Step</span>
          <h2 id="rt-final-h2">Start Your Research Journey</h2>
          <p id="rt-final-p">
            Create a free account and complete the four Research Spectrum courses to build your
            skills and become eligible to apply to the Research Team.
          </p>
          <div className="ctas">
            {canSubmit ? (
              <Link to="/research-team/apply" className="btn btn-white" id="rt-final-cta">
                <span id="rt-final-cta-text">Apply To Research Team</span>
              </Link>
            ) : (
              <Link to="/courses" className="btn btn-white" id="rt-final-cta">
                <span id="rt-final-cta-text">Explore Courses</span>
              </Link>
            )}
            <Link
              to="/faq"
              className="btn btn-ghost"
              style={{ background: 'transparent', borderColor: 'rgba(255,255,255,.35)', color: '#fff' }}
            >
              Read The FAQ
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

export function ResearchTeamSharedSections() {
  return (
    <>
      <WhyJoinSection />
      <ProjectsSection />
      <AuthorshipSection />
      <HowItWorksSection />
    </>
  )
}

export function GuestResearchTeam({ error }: { error: string | null }) {
  return (
    <>
      <GuestHero />
      <ResearchTeamSharedSections />
      <GuestApplicationSection error={error} />
      <FaqSection />
      <FinalCtaSection />
    </>
  )
}
