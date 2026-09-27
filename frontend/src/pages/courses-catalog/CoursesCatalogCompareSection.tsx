import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import type { PublicCatalogCourse } from '../../lib/api/public-catalog'
import { coursesCatalogCompare } from '../../lib/marketing/coursesCatalogCopy'

type CoursesCatalogCompareSectionProps = {
  courses: PublicCatalogCourse[]
}

export function CoursesCatalogCompareSection({ courses }: CoursesCatalogCompareSectionProps) {
  if (courses.length === 0) return null

  return (
    <section className="border-y border-rs-line-2 bg-rs-grad-soft px-5 py-[68px] sm:px-7 sm:py-[88px]">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[660px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={coursesCatalogCompare.kicker}
              title={coursesCatalogCompare.title}
              lead={coursesCatalogCompare.lead}
            />
          </Reveal>
        </div>

        <Reveal>
          <div className="overflow-x-auto rounded-rs-lg border border-rs-line bg-white shadow-rs">
            <table className="w-full min-w-[640px] border-collapse">
              <thead>
                <tr className="border-b-2 border-rs-line">
                  <th className="px-5 py-4 text-left text-sm font-extrabold text-rs-navy">
                    {coursesCatalogCompare.featureColumn}
                  </th>
                  {courses.map((course) => (
                    <th
                      key={course.id}
                      className="px-3 py-4 text-center text-[15.5px] font-extrabold leading-snug tracking-tight text-rs-navy"
                    >
                      {course.title}
                    </th>
                  ))}
                  <th className="bg-rs-sky px-3 py-4 text-center text-[15.5px] font-extrabold leading-snug tracking-tight text-rs-navy">
                    {coursesCatalogCompare.bundleColumn}
                  </th>
                </tr>
              </thead>
              <tbody>
                {coursesCatalogCompare.features.map((feature, rowIndex) => (
                  <tr
                    key={feature}
                    className={rowIndex % 2 === 1 ? 'bg-rs-sky-2' : undefined}
                  >
                    <th className="px-5 py-4 text-left text-sm font-bold text-rs-ink">{feature}</th>
                    {courses.map((course) => (
                      <td key={`${course.id}-${feature}`} className="px-3 py-4 text-center text-rs-muted">
                        —
                      </td>
                    ))}
                    <td className="bg-rs-sky px-3 py-4 text-center text-rs-muted">—</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
