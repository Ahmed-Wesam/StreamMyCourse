import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import {
  DEFAULT_SECTION_HEADINGS,
  effectiveSectionHeading,
  sectionHasText,
  type CoursePageDocument,
} from '../../lib/course-page'
import { courseDetailPathway } from '../../lib/marketing/courseDetailShellCopy'

type CourseDetailEnrollCtaBandProps = {
  courseId: string
  page: CoursePageDocument
}

export function CourseDetailEnrollCtaBand({ courseId, page }: CourseDetailEnrollCtaBandProps) {
  if (!sectionHasText('enrollCta', page)) return null

  const section = page.enrollCta
  const heading = effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.enrollCta)
  const checkoutTo = `/checkout?productType=course&courseId=${encodeURIComponent(courseId)}`

  return (
    <section
      id="enroll"
      aria-labelledby="enroll-heading"
      className="border-b border-rs-line bg-gradient-to-b from-rs-sky-2/60 to-white px-5 py-14 sm:px-7"
    >
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="rounded-2xl border border-rs-line bg-white p-8 shadow-rs sm:p-10">
            <SectionHeader title={heading} align="start" level={2} />
            {section?.body?.trim() ? (
              <p className="mt-4 max-w-[620px] text-lg leading-relaxed text-rs-body">{section.body.trim()}</p>
            ) : null}
            {section?.extraLine?.trim() ? (
              <p className="mt-3 max-w-[620px] text-sm leading-relaxed text-rs-muted">
                {section.extraLine.trim()}
              </p>
            ) : null}
            <div className="mt-8">
              <Button to={checkoutTo} arrow>
                {courseDetailPathway.enrollButton}
              </Button>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
