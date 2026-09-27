import { BookOpen, Clock } from 'lucide-react'
import { Badge } from '../../components/ui/Badge'
import { Reveal } from '../../components/ui/Reveal'
import { isHttpsUrl } from '../../lib/isHttpsUrl'
import { formatUsdMinor } from '../../lib/formatUsdMinor'
import { courseDetailLifetimePill } from '../../lib/marketing/courseDetailShellCopy'
import type { Course } from '../../lib/api/types'
import { CourseDetailBreadcrumb } from './CourseDetailBreadcrumb'
import { courseDetailHeroTitle } from './courseDetailHeroTitle'

type CourseDetailHeroSectionProps = {
  loading: boolean
  course: Course | null
  lessonsCount: number
  moduleCount: number
  error: string | null
}

export function CourseDetailHeroSection({
  loading,
  course,
  lessonsCount,
  moduleCount,
  error,
}: CourseDetailHeroSectionProps) {
  const heroTitle = courseDetailHeroTitle(loading, course, error)
  const breadcrumbTitle = loading ? '' : course?.title ?? ''
  const heroThumbnail = course?.thumbnailUrl && isHttpsUrl(course.thumbnailUrl) ? course.thumbnailUrl : null

  return (
    <section aria-label="Course hero" className="relative overflow-hidden bg-gradient-to-b from-rs-sky-2 to-white px-5 pb-12 pt-8 sm:px-7 sm:pb-16 sm:pt-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(720px_480px_at_85%_0%,rgba(58,134,255,.12),transparent_62%)]"
      />
      <div className="relative mx-auto max-w-wrap">
        <CourseDetailBreadcrumb courseTitle={breadcrumbTitle} />
        <div className="mt-8 grid items-center gap-10 nav:grid-cols-[1.05fr_0.95fr] nav:gap-14">
          <div>
            <Reveal>
              <h1 className="text-[clamp(32px,4.5vw,52px)] font-extrabold leading-[1.08] tracking-tight text-rs-ink">
                {heroTitle}
              </h1>
            </Reveal>
            <Reveal>
              <p className="mt-4 max-w-[560px] text-[17.5px] leading-relaxed text-rs-body">
                {loading ? '' : course?.description ?? ''}
              </p>
            </Reveal>
            {!loading && course ? (
              <Reveal>
                <div className="mt-6 flex flex-wrap items-center gap-2.5">
                  <Badge tone="blue">{courseDetailLifetimePill}</Badge>
                  {typeof course.amountMinor === 'number' && course.amountMinor > 0 ? (
                    <span className="inline-flex items-center rounded-full border border-rs-line bg-white px-3.5 py-1.5 text-xs font-bold text-rs-blue">
                      {formatUsdMinor(course.amountMinor)}
                    </span>
                  ) : null}
                  {course.hasAccess ? <Badge tone="success">Owned</Badge> : null}
                  <span className="inline-flex items-center gap-2 rounded-full border border-rs-line bg-white px-3.5 py-1.5 text-xs font-bold text-rs-navy">
                    <BookOpen className="h-3.5 w-3.5 text-rs-blue" aria-hidden />
                    {lessonsCount} {lessonsCount === 1 ? 'lesson' : 'lessons'}
                  </span>
                  {moduleCount > 0 ? (
                    <span className="inline-flex items-center gap-2 rounded-full border border-rs-line bg-white px-3.5 py-1.5 text-xs font-bold text-rs-navy">
                      {moduleCount} {moduleCount === 1 ? 'module' : 'modules'}
                    </span>
                  ) : null}
                  <span className="inline-flex items-center gap-2 rounded-full border border-rs-line bg-white px-3.5 py-1.5 text-xs font-bold text-rs-navy">
                    <Clock className="h-3.5 w-3.5 text-rs-blue" aria-hidden />
                    Self-paced
                  </span>
                </div>
              </Reveal>
            ) : null}
          </div>
          <Reveal>
            <div className="aspect-video w-full overflow-hidden rounded-2xl border border-rs-line bg-rs-sky-2 shadow-rs">
              {heroThumbnail ? (
                <img src={heroThumbnail} alt="" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center text-sm font-semibold text-rs-muted">
                  Course preview
                </div>
              )}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
