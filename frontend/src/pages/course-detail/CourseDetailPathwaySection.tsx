import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { listPublishedCourses, type PublicCatalogCourse } from '../../lib/api/public-catalog'
import { courseDetailPathway } from '../../lib/marketing/courseDetailShellCopy'

type CourseDetailPathwaySectionProps = {
  courseId: string
  courseTitle: string
}

export function CourseDetailPathwaySection({ courseId, courseTitle }: CourseDetailPathwaySectionProps) {
  const [catalogCourses, setCatalogCourses] = useState<PublicCatalogCourse[] | null>(null)

  useEffect(() => {
    let cancelled = false
    void listPublishedCourses()
      .then((courses) => {
        if (!cancelled) setCatalogCourses(courses)
      })
      .catch(() => {
        if (!cancelled) setCatalogCourses(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const steps = useMemo(() => {
    if (catalogCourses === null) return null
    const byId = new Map(catalogCourses.map((course) => [course.id, course]))
    const ordered: PublicCatalogCourse[] = [...catalogCourses]
    if (!byId.has(courseId)) {
      ordered.push({ id: courseId, title: courseTitle, description: '' })
    }
    return ordered
  }, [catalogCourses, courseId, courseTitle])

  if (!steps || steps.length === 0) return null

  return (
    <section
      id="pathway"
      aria-labelledby="pathway-heading"
      className="border-b border-rs-line bg-rs-sky-2/30 px-5 py-14 sm:px-7"
    >
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <SectionHeader
            kicker={courseDetailPathway.kicker}
            title={courseDetailPathway.title}
            lead={courseDetailPathway.lead}
            align="start"
            level={2}
          />
        </Reveal>
        <Reveal>
          <ol className="mt-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-stretch sm:gap-4">
            {steps.map((step, index) => {
              const isCurrent = step.id === courseId
              return (
                <li key={step.id} className="flex min-w-0 flex-1 flex-col sm:min-w-[140px]">
                  <Link
                    to={`/courses/${step.id}`}
                    aria-label={step.title}
                    aria-current={isCurrent ? 'step' : undefined}
                    className={[
                      'flex h-full flex-col rounded-2xl border px-4 py-4 no-underline transition hover:-translate-y-0.5 hover:shadow-rs-sm',
                      isCurrent
                        ? 'border-rs-blue bg-white shadow-rs ring-2 ring-rs-blue/20'
                        : 'border-rs-line bg-white',
                    ].join(' ')}
                  >
                    <span className="text-[11px] font-extrabold tracking-wide text-rs-blue">
                      Step {index + 1}
                    </span>
                    <span className="mt-2 text-[15px] font-extrabold leading-snug text-rs-ink">
                      {step.title}
                    </span>
                    {isCurrent ? (
                      <span className="mt-2 inline-flex w-fit rounded-full bg-rs-sky px-2.5 py-0.5 text-[11px] font-bold text-rs-blue">
                        {courseDetailPathway.currentCourseBadge}
                      </span>
                    ) : null}
                  </Link>
                </li>
              )
            })}
            <li className="flex min-w-0 flex-1 flex-col sm:min-w-[140px]">
              <Link
                to="/research-team"
                aria-label={courseDetailPathway.researchTeamLabel}
                className="flex h-full flex-col rounded-2xl border border-rs-line bg-white px-4 py-4 no-underline transition hover:-translate-y-0.5 hover:shadow-rs-sm"
              >
                <span className="text-[11px] font-extrabold tracking-wide text-rs-blue">
                  Step {steps.length + 1}
                </span>
                <span className="mt-2 text-[15px] font-extrabold leading-snug text-rs-ink">
                  {courseDetailPathway.researchTeamLabel}
                </span>
              </Link>
            </li>
          </ol>
        </Reveal>
      </div>
    </section>
  )
}
