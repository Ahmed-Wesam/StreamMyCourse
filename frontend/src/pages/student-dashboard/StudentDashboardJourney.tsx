import { Link } from 'react-router-dom'

import { CourseGlyph, IconCheck, IconPeople } from './dashboardIcons'
import { pathwayCoursesOrPrototype, type DashboardPathwayCourse } from './dashboardPathway'

type StudentDashboardJourneyProps = {
  courses: DashboardPathwayCourse[]
}

function segmentStyle(index: number, count: number, done: boolean, nextDone: boolean) {
  const width = count > 0 ? 80 / count : 0
  const left = 10 + index * width
  let className = 'lj-seg inactive'
  let background: string | undefined
  if (done && nextDone) className = 'lj-seg done'
  else if (done !== nextDone) {
    className = 'lj-seg partial'
    background = done
      ? 'linear-gradient(to right,#22c55e,#d8e3fb)'
      : 'linear-gradient(to right,#d8e3fb,#22c55e)'
  }
  return {
    className,
    style: { left: `${left}%`, width: `${width}%`, background },
  }
}

export function StudentDashboardJourney({ courses }: StudentDashboardJourneyProps) {
  const steps = pathwayCoursesOrPrototype(courses)
  const doneCount = steps.filter((course) => course.certified).length
  const eligible = steps.length > 0 && doneCount === steps.length
  const doneStates = [...steps.map((course) => course.certified), eligible]

  return (
    <section className="db">
      <div className="wrap">
        <div className="db-head">
          <div className="ht">
            <h2>Your Learning Journey</h2>
            <span className="htmeta">The complete pathway to Research Team eligibility</span>
          </div>
        </div>
        <div className="lj-wrap reveal">
          <div className="lj">
            {steps.map((course, index) => {
              const seg = segmentStyle(index, steps.length, doneStates[index] === true, doneStates[index + 1] === true)
              return (
                <i key={`seg-${course.courseId}`} className={seg.className} data-seg={index} style={seg.style} />
              )
            })}
            {steps.map((course) => (
              <div key={course.courseId} className={course.certified ? 'ls done' : 'ls notdone'}>
                <div className="node">
                  {course.certified ? <IconCheck /> : <CourseGlyph title={course.title} />}
                </div>
                <span className="lbl">{course.certified ? 'Completed' : 'Not Completed'}</span>
                <h4>
                  {course.href ? <Link to={course.href}>{course.title}</Link> : course.title}
                </h4>
              </div>
            ))}
            <div className={eligible ? 'ls final eligible' : 'ls final'}>
              <div className="node">{eligible ? <IconCheck /> : <IconPeople strokeWidth={1.9} />}</div>
              <span className="lbl">{eligible ? 'Eligible' : 'Goal'}</span>
              <h4>Research Team Eligibility</h4>
              <span className="sub">
                {doneCount} / {steps.length} Completed
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
