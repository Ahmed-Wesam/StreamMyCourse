import { BookOpen, Star } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import type { PublicCatalogCourse } from '../../lib/api/public-catalog'
import { homeBundle, homeCourses } from '../../lib/marketing/homeCopy'

type CatalogState =
  | { status: 'loading' }
  | { status: 'ready'; courses: PublicCatalogCourse[] }
  | { status: 'error'; message: string }

type HomeCoursesSectionProps = {
  catalog: CatalogState
  onRetry: () => void
}

export function HomeCoursesSection({ catalog, onRetry }: HomeCoursesSectionProps) {
  const courses = catalog.status === 'ready' ? catalog.courses : []

  return (
    <section id="courses" className="scroll-mt-24 px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[1100px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={homeCourses.kicker}
              title={homeCourses.title}
              lead={homeCourses.lead}
            />
          </Reveal>
        </div>

        {catalog.status === 'loading' ? (
          <p className="text-center text-rs-body">Loading courses…</p>
        ) : null}

        {catalog.status === 'error' ? (
          <div className="mx-auto flex max-w-lg flex-col items-center gap-4 text-center">
            <p className="text-rs-body">{catalog.message}</p>
            <Button type="button" variant="ghost" onClick={onRetry}>
              {homeCourses.retryLabel}
            </Button>
          </div>
        ) : null}

        {catalog.status === 'ready' && courses.length === 0 ? (
          <p className="text-center text-rs-body">{homeCourses.emptyMessage}</p>
        ) : null}

        {catalog.status === 'ready' && courses.length > 0 ? (
          <>
            <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-2">
              {courses.map((course) => (
                <Reveal key={course.id}>
                  <Card className="flex gap-[18px] rounded-rs px-6 py-[22px] shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1 hover:shadow-rs">
                    <div className="flex size-[50px] shrink-0 items-center justify-center rounded-[14px] border border-[#e2ebff] bg-rs-grad-soft">
                      <BookOpen
                        aria-hidden
                        className="size-[25px] text-rs-blue"
                        strokeWidth={1.9}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="mb-1 text-[17px] font-extrabold leading-snug tracking-tight text-rs-ink">
                        {course.title}
                      </h3>
                      {course.description ? (
                        <p className="mb-3 text-[13.5px] leading-snug text-rs-body">
                          {course.description}
                        </p>
                      ) : null}
                      <div className="flex items-center justify-end gap-3">
                        <Button to={`/courses/${course.id}`} variant="ghost" size="sm" arrow>
                          {homeCourses.viewCourse}
                        </Button>
                      </div>
                    </div>
                  </Card>
                </Reveal>
              ))}
            </div>

            <Reveal className="mt-[22px]">
              <div className="relative overflow-hidden rounded-rs-lg bg-rs-grad px-7 py-8 text-white shadow-rs-lg sm:px-11 sm:py-[42px]">
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 opacity-50 [background-image:radial-gradient(rgba(255,255,255,.10)_1px,transparent_1px)] [background-size:24px_24px]"
                />
                <div className="relative grid items-center gap-6 nav:grid-cols-[1.4fr_auto] nav:gap-[30px]">
                  <div>
                    <span className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-xs font-extrabold uppercase tracking-wider text-rs-blue">
                      <Star aria-hidden className="size-3.5 fill-rs-blue text-rs-blue" />
                      {homeBundle.bestTag}
                    </span>
                    <h3 className="text-[clamp(24px,3vw,32px)] font-extrabold leading-tight tracking-tight">
                      {homeBundle.title}
                    </h3>
                    <p className="mt-2.5 max-w-[440px] text-[15.5px] leading-relaxed text-[#cfe0ff]">
                      {homeBundle.blurb}
                    </p>
                    <div className="mt-[18px] flex flex-wrap gap-2">
                      {courses.map((course) => (
                        <span
                          key={`chip-${course.id}`}
                          className="rounded-full border border-white/20 bg-white/15 px-3 py-1.5 text-[12.5px] font-semibold"
                        >
                          {course.title}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="relative text-center">
                    <Button
                      to="/courses"
                      arrow
                      className="!bg-white !text-rs-blue hover:!-translate-y-0.5 hover:!shadow-[0_20px_40px_-12px_rgba(0,0,0,.3)]"
                    >
                      {homeBundle.cta}
                    </Button>
                  </div>
                </div>
              </div>
            </Reveal>

            <div className="mt-[30px] text-center">
              <Reveal>
                <Button to="/courses" variant="ghost" arrow>
                  {homeCourses.exploreCourses}
                </Button>
              </Reveal>
            </div>
          </>
        ) : null}
      </div>
    </section>
  )
}
