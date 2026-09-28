import { BookOpen } from 'lucide-react'

import { CatalogCourseCardMeta } from '../../components/course/CatalogCourseCardMeta'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import type { PublicCatalogCourse } from '../../lib/api/public-catalog'
import { aboutCourses } from '../../lib/marketing/aboutCopy'

export type AboutCatalogState =
  | { status: 'loading' }
  | { status: 'ready'; courses: PublicCatalogCourse[] }
  | { status: 'error'; message: string }

type AboutCoursesSectionProps = {
  catalog: AboutCatalogState
  onRetry: () => void
}

export function AboutCoursesSection({ catalog, onRetry }: AboutCoursesSectionProps) {
  const courses = catalog.status === 'ready' ? catalog.courses : []

  return (
    <section className="border-y border-rs-line-2 bg-rs-sky-2 px-5 py-20 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="mb-10">
            <SectionHeader
              kicker={aboutCourses.kicker}
              title={aboutCourses.title}
              lead={aboutCourses.lead}
            />
          </div>
        </Reveal>

        {catalog.status === 'loading' ? (
          <p className="text-center text-rs-body">Loading courses…</p>
        ) : null}

        {catalog.status === 'error' ? (
          <div className="mx-auto flex max-w-lg flex-col items-center gap-4 text-center">
            <p className="text-rs-body">{catalog.message}</p>
            <Button type="button" variant="ghost" onClick={onRetry}>
              {aboutCourses.retryLabel}
            </Button>
          </div>
        ) : null}

        {catalog.status === 'ready' && courses.length === 0 ? (
          <p className="text-center text-rs-body">{aboutCourses.emptyMessage}</p>
        ) : null}

        {catalog.status === 'ready' && courses.length > 0 ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {courses.map((course) => (
              <Reveal key={course.id}>
                <Card className="flex flex-col gap-3 rounded-rs-lg px-6 py-[26px] shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1 hover:shadow-rs">
                  <div className="flex size-[46px] items-center justify-center rounded-[13px] border border-[#e2ebff] bg-rs-grad-soft text-rs-blue">
                    <BookOpen aria-hidden className="size-[22px]" strokeWidth={2} />
                  </div>
                  <h3 className="text-lg font-extrabold tracking-tight text-rs-ink">
                    {course.title}
                  </h3>
                  <CatalogCourseCardMeta course={course} />
                  {course.description ? (
                    <p className="flex-1 text-sm leading-relaxed text-rs-body">
                      {course.description}
                    </p>
                  ) : null}
                  <Button
                    to={`/courses/${course.id}`}
                    variant="ghost"
                    size="sm"
                    arrow
                    className="mt-1 w-full justify-center"
                  >
                    {aboutCourses.viewCourse}
                  </Button>
                </Card>
              </Reveal>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  )
}
