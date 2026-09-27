import { BookOpen, Star } from 'lucide-react'

import { ImageWithFallback } from '../../components/figma/ImageWithFallback'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { Badge } from '../../components/ui/Badge'
import type { BundleOffer } from '../../lib/api/types'
import type { PublicCatalogCourse } from '../../lib/api/public-catalog'
import { formatUsdMinor } from '../../lib/formatUsdMinor'
import {
  coursesCatalogGrid,
} from '../../lib/marketing/coursesCatalogCopy'
import { homeBundle } from '../../lib/marketing/homeCopy'
import { type OwnedCoursesScope, viewerOwnsCourse } from '../../lib/ownedFromPurchases'

export type CatalogState =
  | { status: 'loading' }
  | { status: 'ready'; courses: PublicCatalogCourse[] }
  | { status: 'error'; message: string }

type CoursesCatalogGridSectionProps = {
  catalog: CatalogState
  onRetry: () => void
  bundleOffer: BundleOffer | null
  ownership: OwnedCoursesScope | null
}

function CourseThumbnail({ course }: { course: PublicCatalogCourse }) {
  if (course.thumbnailUrl) {
    return (
      <ImageWithFallback
        src={course.thumbnailUrl}
        alt=""
        className="size-[70px] shrink-0 rounded-[18px] border border-[#e2ebff] object-cover"
      />
    )
  }

  return (
    <div className="flex size-[70px] shrink-0 items-center justify-center rounded-[18px] border border-[#e2ebff] bg-rs-grad-soft">
      <BookOpen aria-hidden className="size-[34px] text-rs-blue" strokeWidth={1.9} />
    </div>
  )
}

export function CoursesCatalogGridSection({ catalog, onRetry, bundleOffer, ownership }: CoursesCatalogGridSectionProps) {
  const courses = catalog.status === 'ready' ? catalog.courses : []

  return (
    <section id="courses-catalog" className="scroll-mt-24 px-5 py-[68px] sm:px-7 sm:py-[88px]">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[660px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={coursesCatalogGrid.kicker}
              title={coursesCatalogGrid.title}
              lead={coursesCatalogGrid.lead}
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
              {coursesCatalogGrid.retryLabel}
            </Button>
          </div>
        ) : null}

        {catalog.status === 'ready' && courses.length === 0 ? (
          <p className="text-center text-rs-body">{coursesCatalogGrid.emptyMessage}</p>
        ) : null}

        {catalog.status === 'ready' && courses.length > 0 ? (
          <div className="grid grid-cols-1 gap-[22px] lg:grid-cols-2">
            {courses.map((course) => (
              <Reveal key={course.id}>
                <Card className="group relative flex h-full flex-col overflow-hidden rounded-rs-lg border border-rs-line px-[30px] py-7 shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1 hover:border-[#bdd0ff] hover:shadow-[0_22px_48px_-18px_rgba(20,53,140,.22)]">
                  <div
                    aria-hidden
                    className="absolute inset-x-0 top-0 h-1 origin-left scale-x-0 bg-rs-grad-cta transition duration-300 group-hover:scale-x-100"
                  />
                  <div className="mb-4 flex items-center gap-4">
                    <CourseThumbnail course={course} />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-xl font-extrabold leading-snug tracking-tight text-rs-ink">
                          {course.title}
                        </h3>
                        {ownership && viewerOwnsCourse(ownership, course.id, course.hasAccess) ? (
                          <Badge tone="success">Owned</Badge>
                        ) : null}
                      </div>
                      <p className="mt-1 text-[22px] font-extrabold leading-none tracking-tight text-rs-blue">
                        {typeof course.amountMinor === 'number' && course.amountMinor > 0
                          ? formatUsdMinor(course.amountMinor)
                          : coursesCatalogGrid.pricingPrimary}
                        <span className="mt-0.5 block text-xs font-semibold tracking-normal text-rs-muted">
                          {coursesCatalogGrid.pricingSecondary}
                        </span>
                      </p>
                    </div>
                  </div>
                  {course.description ? (
                    <p className="mb-5 text-[14.5px] leading-snug text-rs-body">{course.description}</p>
                  ) : null}
                  <div className="mt-auto flex flex-wrap gap-2.5">
                    <Button to={`/courses/${course.id}`} className="min-w-0 flex-1" size="sm">
                      {coursesCatalogGrid.viewCourse}
                    </Button>
                    <Button
                      to={`/courses/${course.id}#curriculum`}
                      variant="ghost"
                      className="min-w-0 flex-1"
                      size="sm"
                    >
                      {coursesCatalogGrid.viewCurriculum}
                    </Button>
                  </div>
                </Card>
              </Reveal>
            ))}

            <Reveal className="lg:col-span-2">
              <div className="relative grid items-center gap-6 overflow-hidden rounded-rs-lg bg-rs-grad px-7 py-8 text-white shadow-rs-lg sm:px-10 sm:py-10 nav:grid-cols-[1.4fr_auto] nav:gap-[30px]">
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 opacity-50 [background-image:radial-gradient(rgba(255,255,255,.10)_1px,transparent_1px)] [background-size:24px_24px]"
                />
                <div className="relative">
                  <span className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-xs font-extrabold uppercase tracking-wider text-rs-blue">
                    <Star aria-hidden className="size-3.5 fill-rs-blue text-rs-blue" />
                    {homeBundle.bestTag}
                  </span>
                  <h3 className="text-[clamp(22px,2.6vw,28px)] font-extrabold leading-tight tracking-tight">
                    {homeBundle.title}
                  </h3>
                  <p className="mt-2 max-w-[440px] text-[15px] leading-relaxed text-[#cfe0ff]">
                    {homeBundle.blurb}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
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
                  {bundleOffer ? (
                    <p className="mb-3 text-2xl font-extrabold">{formatUsdMinor(bundleOffer.amountMinor)}</p>
                  ) : null}
                  <Button
                    to="/checkout?productType=bundle"
                    arrow
                    className="!bg-white !text-rs-blue hover:!-translate-y-0.5 hover:!shadow-[0_20px_40px_-12px_rgba(0,0,0,.3)]"
                  >
                    {homeBundle.cta}
                  </Button>
                </div>
              </div>
            </Reveal>
          </div>
        ) : null}
      </div>
    </section>
  )
}
