import { Link } from 'react-router-dom'

import type { StudentDashboardCourseRow } from '../../lib/studentDashboard'
import { CourseGlyph, IconArrow, IconBook } from './dashboardIcons'

type StudentDashboardContinueSectionProps = {
  rows: StudentDashboardCourseRow[]
}

function percentLabel(percent: StudentDashboardCourseRow['percentComplete']): string {
  if (percent === 'unavailable') return '—'
  return `${Math.round(percent)}%`
}

export function StudentDashboardContinueSection({ rows }: StudentDashboardContinueSectionProps) {
  return (
    <section className="db">
      <div className="wrap">
        <div className="db-head">
          <div className="ht">
            <h2>Continue Learning</h2>
            <span className="htmeta">Pick up where you left off</span>
          </div>
          <Link to="/courses" className="htlink">
            View all courses
            <IconArrow strokeWidth={2.4} />
          </Link>
        </div>
        {rows.length === 0 ? (
          <div className="cl-empty" data-testid="student-dashboard-empty">
            <div className="empty-state reveal">
              <div className="es-ic">
                <IconBook strokeWidth={1.9} />
              </div>
              <h2>You have not enrolled in any courses yet.</h2>
              <p>Browse the course catalog and enroll in your first course to get started on your research journey.</p>
              <div className="btn-w">
                <Link to="/courses#courses-catalog" className="btn btn-primary" style={{ fontSize: 16, padding: '14px 28px' }}>
                  Explore Courses
                  <IconArrow />
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <div className="cont-grid" data-testid="student-dashboard-continue">
            {rows.map((row, index) => {
              const width = row.percentComplete === 'unavailable' ? 0 : Math.max(0, Math.min(100, row.percentComplete))
              return (
                <div
                  key={row.courseId}
                  className="clc reveal"
                  data-d={String((index % 4) + 1)}
                  data-testid={`student-dashboard-course-${row.courseId}`}
                >
                  <div className="cct">
                    <div className="cci">
                      <CourseGlyph title={row.title} />
                    </div>
                    <div className="ctxt">
                      <h3>
                        <Link to={`/courses/${row.courseId}`}>{row.title}</Link>
                      </h3>
                      {row.subline ? (
                        <span className="tag">
                          Module {row.subline.moduleIndex} of {row.subline.moduleCount}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <p className="lesson">
                    {row.percentComplete === 'unavailable' ? (
                      'Progress unavailable'
                    ) : row.subline ? (
                      <>
                        Current lesson<b>{row.subline.lessonTitle}</b>
                      </>
                    ) : (
                      <>
                        Current lesson<b>{row.title}</b>
                      </>
                    )}
                  </p>
                  <div className="pwrap">
                    <div className="ppct">
                      <span>Progress</span>
                      <b>{percentLabel(row.percentComplete)}</b>
                    </div>
                    <div className="pbar">
                      <i style={{ width: `${width}%` }} />
                    </div>
                  </div>
                  <Link to={row.continueHref} className="btn btn-primary">
                    Continue Course
                    <IconArrow />
                  </Link>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
