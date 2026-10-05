import { Link } from 'react-router-dom'

import { ArrowIcon, RtIcon } from './rtIcon'
import { ResearchTeamEligibilitySection } from './ResearchTeamEligibilitySection'
import {
  ResearchTeamProgressPanel,
  type ResearchTeamProgressView,
} from './ResearchTeamProgressPanel'
import { FaqSection, FinalCtaSection, ResearchTeamSharedSections } from './ResearchTeamGuest'

function certifiedCount(progress: ResearchTeamProgressView): number {
  return progress.courses.filter((course) => course.certified).length
}

function MemberHero({ progress }: { progress: ResearchTeamProgressView }) {
  const total = progress.courses.length
  const certified = certifiedCount(progress)
  const pct = total === 0 ? 0 : Math.round((certified / total) * 100)
  const learnLabel = certified > 0 ? 'Continue Learning' : 'Explore Courses'

  return (
    <section className="rt-hero">
      <div className="wrap">
        <div className="rt-hero-grid">
          <div>
            <div className="eyebrow reveal">
              <span className="dot" />
              Research Spectrum Program
            </div>
            <h1 className="reveal" data-d="1" id="rt-hero-h1">
              {progress.eligible ? (
                <>
                  You&apos;ve completed the <span className="g">Research Spectrum pathway</span>.
                </>
              ) : (
                <>
                  The <span className="g">Research Team</span>
                  <br />
                  Real Projects. Real Publications.
                </>
              )}
            </h1>
            <p className="sub reveal" data-d="2" id="rt-hero-sub">
              {progress.eligible
                ? 'Now put those skills to work on real research projects, publications, and collaborative studies.'
                : 'Join a community of researchers turning coursework into published evidence. Research Team members co-author systematic reviews, meta-analyses, and original studies — with mentorship from experienced researchers every step of the way.'}
            </p>
            <div className="rt-hero-ctas reveal" data-d="3">
              {progress.canSubmit ? (
                <Link to="/research-team/apply" className="btn btn-primary" id="rt-hero-cta">
                  <span id="rt-hero-cta-text">Apply To Research Team</span>
                  <ArrowIcon />
                </Link>
              ) : (
                <Link to="/courses" className="btn btn-primary" id="rt-hero-cta">
                  <span id="rt-hero-cta-text">{learnLabel}</span>
                  <ArrowIcon />
                </Link>
              )}
              <a href="#eligibility" className="btn btn-ghost" id="rt-hero-secondary-link">
                <span id="rt-hero-secondary-link-text">View Eligibility Requirements</span>
              </a>
            </div>
            <div className="rt-personal-strip reveal" data-d="4" id="rt-personal-strip">
              <RtIcon strokeWidth="2.2">
                <circle cx="12" cy="8" r="5" />
                <path d="M20 21a8 8 0 0 0-16 0" />
              </RtIcon>
              <span id="rt-personal-msg">Welcome, complete your courses to become eligible to apply.</span>
            </div>
          </div>
          <div className="rt-hero-card reveal" data-d="2">
            <h3>Your Research Team Status</h3>
            <div className={`rt-status-badge ${progress.canSubmit ? 'rtb-eligible' : 'rtb-not-eligible'}`} id="rt-hero-badge">
              <RtIcon strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </RtIcon>
              {progress.canSubmit ? 'Eligible To Apply' : 'Not Yet Eligible'}
            </div>
            {total > 0 ? (
              <>
                <div className="rt-prog-row" id="rt-hero-prog-row">
                  <span id="rt-prog-label-hero">
                    {certified} of {total} requirements completed
                  </span>
                  <b id="rt-hero-pct">{pct}%</b>
                </div>
                <div className="rt-pbar-track" id="rt-hero-pbar-track">
                  <div className="rt-pbar-fill" id="rt-hero-bar" style={{ width: `${pct}%` }} />
                </div>
                <p className="rt-prog-sub" id="rt-prog-sub">
                  {progress.canSubmit
                    ? "You've completed all eligibility requirements and can now apply to the Research Team."
                    : 'Complete every Research Spectrum course to unlock the application.'}
                </p>
                <div className="rt-mini-grid" id="rt-hero-mini-grid">
                  <div className="rt-mini">
                    <div className="val" id="rt-mini-courses">
                      {certified}
                      <span style={{ fontSize: 16, color: 'var(--muted)' }}>/{total}</span>
                    </div>
                    <div className="lbl">Courses Completed</div>
                  </div>
                  <div className="rt-mini">
                    <div className="val" id="rt-mini-certs">
                      {pct}
                      <span style={{ fontSize: 16, color: 'var(--muted)' }}>%</span>
                    </div>
                    <div className="lbl">Eligibility Progress</div>
                  </div>
                </div>
              </>
            ) : null}
            <a href="#eligibility" className="btn btn-ghost btn-sm" style={{ width: '100%' }} id="rt-hero-secondary-cta">
              <span id="rt-hero-secondary-text">View Eligibility Requirements</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

function AchievementSection({ progress }: { progress: ResearchTeamProgressView }) {
  const total = progress.courses.length
  const certified = certifiedCount(progress)
  const pct = total === 0 ? 0 : Math.round((certified / total) * 100)
  const unlocked = progress.canSubmit

  return (
    <section className="sec" style={{ padding: 0 }} id="rt-achievement-section">
      <div className="wrap">
        <div className={unlocked ? 'rt-achievement gold reveal' : 'rt-achievement reveal'} id="rt-achievement">
          <div className="rt-achievement-body">
            <div className="rt-achievement-icon" id="rt-ach-icon">
              <RtIcon strokeWidth="2.2">
                <path d="M12 15a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" />
                <path d="m8.5 13.5-1 6.5 4.5-2 4.5 2-1-6.5" />
              </RtIcon>
            </div>
            <div>
              <span className="rt-achievement-kicker" id="rt-ach-kicker">
                {unlocked ? 'Eligibility Unlocked' : 'In Progress'}
              </span>
              <h2 id="rt-ach-h">{unlocked ? 'Research Team Eligibility Unlocked' : 'Research Team Progress'}</h2>
              <p id="rt-ach-d">
                {unlocked
                  ? "You've completed the full Research Spectrum pathway and unlocked eligibility for Research Team membership. Apply your skills to real research projects, collaborate with fellow researchers, and contribute to publishable scientific work."
                  : "You're building toward Research Team eligibility. Complete all four Research Spectrum courses to unlock opportunities to participate in real research projects, publications, and authorship opportunities."}
              </p>
              {unlocked ? (
                <div className="rt-ach-benefits" id="rt-ach-benefits">
                  <span className="rt-ach-chip">Research Projects</span>
                  <span className="rt-ach-chip">Publications</span>
                  <span className="rt-ach-chip">Authorship</span>
                  <span className="rt-ach-chip">Team Access</span>
                </div>
              ) : (
                <div className="rt-ach-progress" id="rt-ach-progress">
                  <div className="rt-prog-row">
                    <span id="rt-ach-prog-label">
                      {certified} of {total} Courses Completed
                    </span>
                    <b id="rt-ach-pct">{pct}%</b>
                  </div>
                  <div className="rt-pbar-track">
                    <div className="rt-pbar-fill" id="rt-ach-bar" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )}
            </div>
          </div>
          {unlocked ? (
            <Link to="/research-team/apply" className="btn btn-white" id="rt-ach-cta">
              <span id="rt-ach-cta-text">Apply To Research Team</span>
            </Link>
          ) : (
            <Link to="/courses" className="btn btn-white" id="rt-ach-cta">
              <span id="rt-ach-cta-text">{certified > 0 ? 'Continue Learning' : 'Explore Courses'}</span>
            </Link>
          )}
        </div>
      </div>
    </section>
  )
}

function MemberStatus({ progress }: { progress: ResearchTeamProgressView }) {
  return (
    <section className="sec sec-tight" id="application-status">
      <div className="wrap">
        <div className="sec-head">
          <span className="kicker reveal" id="rt-app-sec-kicker">
            {progress.canSubmit ? 'Ready To Apply' : 'Your Application'}
          </span>
          <h2 className="title reveal" data-d="1" id="rt-app-sec-h2">
            {progress.canSubmit ? 'Apply To The Research Team' : 'Application Status'}
          </h2>
          <p className="lead rt-status-lead reveal" data-d="2" id="rt-app-sec-lead">
            {progress.canSubmit
              ? "You've completed all eligibility requirements. Submit your application to join the Research Team."
              : 'Your status updates automatically as your application moves through review.'}
          </p>
        </div>
        <div className="rt-app-card reveal">
          <ResearchTeamProgressPanel progress={progress} />
        </div>
      </div>
    </section>
  )
}

export function MemberResearchTeam({ progress }: { progress: ResearchTeamProgressView }) {
  const courses = progress.courses.map((course) => ({
    id: course.courseId,
    title: course.title,
    certified: course.certified,
  }))

  return (
    <>
      <MemberHero progress={progress} />
      {courses.length > 0 ? <AchievementSection progress={progress} /> : null}
      <ResearchTeamSharedSections />
      <ResearchTeamEligibilitySection courses={courses} />
      <MemberStatus progress={progress} />
      <FaqSection />
      <FinalCtaSection canSubmit={progress.canSubmit} />
    </>
  )
}
