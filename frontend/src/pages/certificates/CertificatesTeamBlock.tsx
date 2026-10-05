import { Link } from 'react-router-dom'

import { pathwayCoursesOrPrototype, type DashboardPathwayCourse } from '../student-dashboard/dashboardPathway'

type CertificatesTeamBlockProps = {
  courses: DashboardPathwayCourse[]
  allComplete: boolean
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: 11, height: 11 }} aria-hidden>
      <path d="M12 2l2.4 7.4H22l-6 4.4 2.3 7.2L12 16.6 5.7 21l2.3-7.2-6-4.4h7.6z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function PendingIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="9" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

export function CertificatesTeamBlock({ courses, allComplete }: CertificatesTeamBlockProps) {
  const listed = courses.length > 0 ? courses : pathwayCoursesOrPrototype([])
  const done = listed.filter((course) => course.certified).length
  const total = listed.length
  const pct = total === 0 ? 0 : Math.round((done / total) * 100)

  return (
    <section className="db">
      <div className="wrap">
        <div className={`team reveal${allComplete ? ' team-eligible' : ''}`}>
          <div className="team-grid">
            <div>
              <span className="kicker-w">
                <StarIcon />
                {allComplete ? 'Achievement Unlocked' : 'Pathway Goal'}
              </span>
              <h2>{allComplete ? "You're Eligible To Apply" : 'Research Team Eligibility'}</h2>
              <p className="lead">
                {allComplete ? (
                  <>
                    Completing all four Research Spectrum courses makes you eligible to apply for the Research
                    Spectrum Research Team.{' '}
                    <strong style={{ color: '#fff' }}>Eligibility does not guarantee acceptance.</strong> Selection
                    involves performance review, assignments, interview, and skills assessment.
                  </>
                ) : (
                  'Complete all four courses to become eligible to apply for the Research Spectrum Research Team and join real-world publication projects.'
                )}
              </p>
              {allComplete ? null : (
                <div className="pwrap">
                  <div className="ppct">
                    <span>
                      {done} of {total} completed
                    </span>
                    <span>{pct}%</span>
                  </div>
                  <div className="pbar">
                    <i style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )}
              <div className="btn-w">
                {allComplete ? (
                  <Link to="/research-team" className="btn btn-white">
                    Apply For The Research Team
                    <ArrowIcon />
                  </Link>
                ) : (
                  <Link to="/courses#courses-catalog" className="btn btn-white">
                    Explore Courses
                    <ArrowIcon />
                  </Link>
                )}
              </div>
            </div>
            <div className="team-list">
              {listed.map((course) => {
                const complete = course.certified
                return (
                  <div key={course.courseId} className={complete ? 'item' : 'item pending'}>
                    <div className={complete ? 'it-ic done' : 'it-ic pending'}>
                      {complete ? <CheckIcon /> : <PendingIcon />}
                    </div>
                    <div className="it-name">{course.title}</div>
                    <span className={complete ? 'it-status done' : 'it-status pending'}>
                      {complete ? 'Done' : 'Not Yet Completed'}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
