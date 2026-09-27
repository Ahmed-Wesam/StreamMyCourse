import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { courseDetailShellSections } from '../../lib/marketing/courseDetailShellCopy'

export function CourseDetailShellSections() {
  return (
    <>
      {courseDetailShellSections.map((section) => (
        <section
          key={section.id}
          id={section.id}
          aria-labelledby={`${section.id}-heading`}
          className="border-b border-rs-line bg-white px-5 py-14 sm:px-7"
        >
          <div className="mx-auto max-w-wrap">
            <Reveal>
              <SectionHeader
                kicker={section.kicker}
                title={section.title}
                lead={section.lead}
                align="start"
              />
            </Reveal>
          </div>
        </section>
      ))}
    </>
  )
}
