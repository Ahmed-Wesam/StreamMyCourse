import { Clock } from 'lucide-react'

import type { PublicCatalogCourse } from '../../lib/api/public-catalog'

type CatalogCourseCardMetaProps = {
  course: PublicCatalogCourse
  /** Catalog grid shows skills; home/about omit the list. */
  showSkills?: boolean
  skillsLabel?: string
  className?: string
}

export function CatalogCourseCardMeta({
  course,
  showSkills = false,
  skillsLabel = 'Key skills',
  className = '',
}: CatalogCourseCardMetaProps) {
  const level = course.level?.trim()
  const hasHours = typeof course.estimatedHours === 'number' && course.estimatedHours > 0
  const skills =
    showSkills && course.catalogSkills?.length
      ? course.catalogSkills.map((s) => s.trim()).filter(Boolean)
      : []
  const hasSkills = skills.length > 0

  if (!level && !hasHours && !hasSkills) {
    return null
  }

  return (
    <div className={className}>
      {level || hasHours ? (
        <div className="flex flex-wrap items-center gap-2">
          {level ? (
            <span className="inline-flex items-center rounded-full border border-rs-line bg-white px-3 py-1 text-xs font-bold text-rs-navy">
              {level}
            </span>
          ) : null}
          {hasHours ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-rs-line bg-white px-3 py-1 text-xs font-bold text-rs-navy">
              <Clock className="size-3.5 text-rs-blue" aria-hidden />
              ~{course.estimatedHours} Hours
            </span>
          ) : null}
        </div>
      ) : null}
      {hasSkills ? (
        <div className={level || hasHours ? 'mt-3' : undefined}>
          <p className="text-[11px] font-extrabold uppercase tracking-wider text-rs-muted">
            {skillsLabel}
          </p>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {skills.map((skill) => (
              <li
                key={skill}
                className="rounded-full border border-[#e2ebff] bg-rs-sky-2 px-2.5 py-1 text-[12px] font-semibold text-rs-navy"
              >
                {skill}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
