import type { ReactNode } from 'react'

import { CheckIcon, RtIcon } from './rtIcon'

type ResearchTeamEligibilityCourse = {
  id: string
  title: string
  certified: boolean
}

function BookIcon() {
  return (
    <RtIcon>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
    </RtIcon>
  )
}

function iconFor(title: string): ReactNode {
  const name = title.toLowerCase()
  if (name.includes('statistic')) {
    return (
      <RtIcon>
        <path d="M3 3v18h18" />
        <rect x="7" y="13" width="3" height="5" rx="1" />
        <rect x="12" y="9" width="3" height="9" rx="1" />
        <rect x="17" y="5" width="3" height="13" rx="1" />
      </RtIcon>
    )
  }
  if (name.includes('writing')) {
    return (
      <RtIcon>
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
      </RtIcon>
    )
  }
  if (name.includes('systematic') || name.includes('meta')) {
    return (
      <RtIcon>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </RtIcon>
    )
  }
  return <BookIcon />
}

type ResearchTeamEligibilitySectionProps = {
  courses: ResearchTeamEligibilityCourse[]
}

export function ResearchTeamEligibilitySection({ courses }: ResearchTeamEligibilitySectionProps) {
  if (courses.length === 0) return null

  return (
    <section className="sec sec-tight" id="eligibility">
      <div className="wrap">
        <div className="sec-head">
          <span className="kicker reveal" id="rt-elig-sec-kicker">
            Before You Apply
          </span>
          <h2 className="title reveal" data-d="1" id="rt-elig-sec-h2">
            Eligibility Requirements
          </h2>
          <p className="lead reveal" data-d="2" id="rt-elig-sec-lead">
            Complete all four Research Spectrum courses to unlock the application.
          </p>
        </div>
        <div className="rt-req-grid">
          {courses.map((course, index) => (
            <div
              className={course.certified ? 'rt-req-card reveal completed' : 'rt-req-card reveal'}
              data-d={String((index % 4) + 1)}
              key={course.id}
            >
              <div className="req-top">
                <div className="req-icon">{iconFor(course.title)}</div>
                {course.certified ? (
                  <span className="req-status completed">
                    <CheckIcon /> Completed
                  </span>
                ) : (
                  <span className="req-status pending">Not Yet Completed</span>
                )}
              </div>
              <h3 data-testid="research-team-required-course">{course.title}</h3>
              <div className="rt-req-prog">
                <i style={{ width: course.certified ? '100%' : '0%' }} />
              </div>
              {course.certified ? (
                <div className="rt-req-cert earned">
                  <CheckIcon /> Certificate Earned
                </div>
              ) : (
                <div className="rt-req-cert not-earned">
                  <RtIcon strokeWidth="1.5">
                    <circle cx="12" cy="12" r="9" />
                  </RtIcon>
                  Certificate Not Yet Earned
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="rt-elig-note reveal" data-d="2" id="rt-elig-note">
          <RtIcon strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </RtIcon>
          Eligibility does not guarantee acceptance. Selection considers interviews, course
          performance, assignments, English proficiency, and research skills.
        </div>
      </div>
    </section>
  )
}
