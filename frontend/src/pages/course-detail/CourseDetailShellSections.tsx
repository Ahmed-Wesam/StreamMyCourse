import type { ReactNode } from 'react'

import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import {
  DEFAULT_SECTION_HEADINGS,
  effectiveSectionHeading,
  sectionHasText,
  type CoursePageDocument,
  type CoursePageHandsOnSection,
  type CoursePageListSection,
  type CoursePageProblemSection,
} from '../../lib/course-page'
import type { Course } from '../../lib/api/types'
import { CourseDetailEnrollCtaBand } from './CourseDetailEnrollCtaBand'
import { CourseDetailPathwaySection } from './CourseDetailPathwaySection'
import { coursePageFromCourse } from './coursePageFromCourse'

type CourseDetailShellSectionsProps = {
  course: Course
  courseId: string
  previewOnly: boolean
  needsAccess: boolean
}

function ShellSectionFrame({
  id,
  children,
}: {
  id: string
  children: ReactNode
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className="border-b border-rs-line bg-white px-5 py-14 sm:px-7"
    >
      <div className="mx-auto max-w-wrap">{children}</div>
    </section>
  )
}

function ListItems({ items }: { items: string[] }) {
  const visible = items.map((item) => item.trim()).filter(Boolean)
  if (visible.length === 0) return null
  return (
    <ul className="mt-6 list-disc space-y-2 pl-5 text-[16px] leading-relaxed text-rs-body">
      {visible.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

function ListPageSection({
  id,
  kicker,
  section,
  defaultHeading,
}: {
  id: string
  kicker: string
  section: CoursePageListSection
  defaultHeading: string
}) {
  const title = effectiveSectionHeading(section, defaultHeading)
  const lead = section.lead?.trim()
  return (
    <ShellSectionFrame id={id}>
      <Reveal>
        <SectionHeader kicker={kicker} title={title} lead={lead} align="start" level={2} />
        <ListItems items={section.items ?? []} />
      </Reveal>
    </ShellSectionFrame>
  )
}

function ProblemSection({ section }: { section: CoursePageProblemSection }) {
  const title = effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.problem)
  const lead = section.lead?.trim()
  const calloutTitle = section.calloutTitle?.trim()
  const calloutBody = section.calloutBody?.trim()
  return (
    <ShellSectionFrame id="problem">
      <Reveal>
        <SectionHeader kicker="The challenge" title={title} lead={lead} align="start" level={2} />
        <ListItems items={section.items ?? []} />
        {calloutTitle || calloutBody ? (
          <div className="mt-8 rounded-2xl border border-[#cfdcfb] bg-rs-sky-2/50 p-6">
            {calloutTitle ? <p className="text-sm font-extrabold text-rs-navy">{calloutTitle}</p> : null}
            {calloutBody ? (
              <p className={calloutTitle ? 'mt-2 text-sm leading-relaxed text-rs-body' : 'text-sm leading-relaxed text-rs-body'}>
                {calloutBody}
              </p>
            ) : null}
          </div>
        ) : null}
      </Reveal>
    </ShellSectionFrame>
  )
}

function HandsOnSection({ section }: { section: CoursePageHandsOnSection }) {
  const title = effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.handsOn)
  const lead = section.lead?.trim()
  const cards = (section.cards ?? []).filter((card) => card.title?.trim() || card.body?.trim())
  const closing = section.closingNote?.trim()
  return (
    <ShellSectionFrame id="hands-on">
      <Reveal>
        <SectionHeader kicker="Hands-on" title={title} lead={lead} align="start" level={2} />
        {cards.length > 0 ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {cards.map((card, index) => {
              const cardTitle = card.title?.trim()
              const cardBody = card.body?.trim()
              const key = cardTitle || cardBody || String(index)
              return (
                <div key={key} className="rounded-2xl border border-rs-line bg-rs-sky-2/30 p-5">
                  {cardTitle ? <h3 className="text-base font-extrabold text-rs-ink">{cardTitle}</h3> : null}
                  {cardBody ? (
                    <p className={cardTitle ? 'mt-2 text-sm leading-relaxed text-rs-body' : 'text-sm leading-relaxed text-rs-body'}>
                      {cardBody}
                    </p>
                  ) : null}
                </div>
              )
            })}
          </div>
        ) : null}
        {closing ? <p className="mt-6 text-sm leading-relaxed text-rs-muted">{closing}</p> : null}
      </Reveal>
    </ShellSectionFrame>
  )
}

function HighlightsSection({ page }: { page: CoursePageDocument }) {
  const section = page.highlights
  if (!section) return null
  const title = effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.highlights)
  const lead = section.lead?.trim()
  const closing = section.closingNote?.trim()
  return (
    <ShellSectionFrame id="highlights">
      <Reveal>
        <SectionHeader kicker="Highlights" title={title} lead={lead} align="start" level={2} />
        <ListItems items={section.items ?? []} />
        {closing ? <p className="mt-6 text-sm leading-relaxed text-rs-muted">{closing}</p> : null}
      </Reveal>
    </ShellSectionFrame>
  )
}

function AssessmentSection({ page }: { page: CoursePageDocument }) {
  const section = page.assessment
  if (!section) return null
  const title = effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.assessment)
  const lead = section.lead?.trim()
  const steps = (section.steps ?? []).filter((step) => step.title?.trim() || step.body?.trim())
  return (
    <ShellSectionFrame id="assessment">
      <Reveal>
        <SectionHeader kicker="Assessment" title={title} lead={lead} align="start" level={2} />
        {steps.length > 0 ? (
          <ol className="mt-8 space-y-4">
            {steps.map((step, index) => {
              const stepTitle = step.title?.trim()
              const stepBody = step.body?.trim()
              const key = stepTitle || stepBody || String(index)
              return (
                <li key={key} className="flex gap-4 rounded-2xl border border-rs-line bg-white p-5">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-rs-grad-cta text-sm font-extrabold text-white">
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    {stepTitle ? <p className="font-extrabold text-rs-ink">{stepTitle}</p> : null}
                    {stepBody ? (
                      <p className={stepTitle ? 'mt-1 text-sm leading-relaxed text-rs-body' : 'text-sm leading-relaxed text-rs-body'}>
                        {stepBody}
                      </p>
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ol>
        ) : null}
      </Reveal>
    </ShellSectionFrame>
  )
}

function viewerHasAccess(course: Course): boolean {
  if (course.hasAccess === true || course.enrolled === true) return true
  return false
}

export function CourseDetailShellSections({
  course,
  courseId,
  previewOnly,
  needsAccess,
}: CourseDetailShellSectionsProps) {
  const page = coursePageFromCourse(course)
  const showEnrollBand = (previewOnly || needsAccess) && !viewerHasAccess(course)

  return (
    <>
      {sectionHasText('problem', page) && page.problem ? <ProblemSection section={page.problem} /> : null}
      {sectionHasText('outcomes', page) && page.outcomes ? (
        <ListPageSection
          id="outcomes"
          kicker="Outcomes"
          section={page.outcomes}
          defaultHeading={DEFAULT_SECTION_HEADINGS.outcomes}
        />
      ) : null}
      {sectionHasText('inside', page) && page.inside ? (
        <ListPageSection
          id="inside"
          kicker="Inside the course"
          section={page.inside}
          defaultHeading={DEFAULT_SECTION_HEADINGS.inside}
        />
      ) : null}
      {sectionHasText('handsOn', page) && page.handsOn ? <HandsOnSection section={page.handsOn} /> : null}
      {sectionHasText('highlights', page) ? <HighlightsSection page={page} /> : null}
      {sectionHasText('audience', page) && page.audience ? (
        <ListPageSection
          id="audience"
          kicker="Audience"
          section={page.audience}
          defaultHeading={DEFAULT_SECTION_HEADINGS.audience}
        />
      ) : null}
      {sectionHasText('assessment', page) ? <AssessmentSection page={page} /> : null}
      <CourseDetailPathwaySection courseId={courseId} courseTitle={course.title} />
      {showEnrollBand ? <CourseDetailEnrollCtaBand courseId={courseId} page={page} /> : null}
    </>
  )
}
