import { Link } from 'react-router-dom'

import { pathwayCoursesOrPrototype, type DashboardPathwayCourse } from './dashboardPathway'
import { IconArrow, IconCheck, IconLock, IconStar } from './dashboardIcons'

type StudentDashboardResearchTeamBlockProps = {
  /** True when the Research Team API returned no required courses. */
  closed: boolean
  courses: DashboardPathwayCourse[]
}

export function StudentDashboardResearchTeamBlock({
  closed,
  courses,
}: StudentDashboardResearchTeamBlockProps) {
  const listed = courses.length > 0 ? courses : pathwayCoursesOrPrototype([])
  const done = courses.filter((course) => course.certified).length
  const total = courses.length > 0 ? courses.length : listed.length
  const pct = total === 0 ? 0 : Math.round((done / total) * 100)

  return (
    <section className="db">
      <div className="wrap">
        <div className="team reveal" data-testid="student-dashboard-research-team">
          <div className="team-grid">
            <div>
              <span className="kicker-w">
                <IconStar /> Pathway Goal
              </span>
              <h2>Research Team Eligibility</h2>
              <p className="lead">
                {closed
                  ? 'Applications are not open yet.'
                  : 'Complete all four courses to become eligible to apply for the Research Spectrum Research Team and join real-world publication projects.'}
              </p>
              {closed ? null : (
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
                <Link to="/research-team" className="btn btn-white">
                  Learn More
                  <IconArrow />
                </Link>
                <Link
                  to="/courses#courses-catalog"
                  className="btn"
                  style={{ background: 'transparent', color: '#fff', border: '1.5px solid rgba(255,255,255,.5)' }}
                >
                  Explore Courses
                </Link>
              </div>
            </div>
            <div className="team-list">
              {listed.map((course) => {
                const complete = course.certified
                return (
                  <div key={course.courseId} className={complete ? 'item' : 'item lock'}>
                    <div className={complete ? 'it-ic done' : 'it-ic lock'}>
                      {complete ? <IconCheck strokeWidth={2.8} /> : <IconLock />}
                    </div>
                    <div className="it-name">{course.title}</div>
                    <span className={complete ? 'it-status done' : 'it-status lock'}>
                      {complete ? 'Done' : 'Locked'}
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
