import type { CoursePageDocument } from '../../lib/course-page'
import type { Course } from '../../lib/api/types'

/** Map GET /courses/:id page fields on `Course` into a `CoursePageDocument`. */
export function coursePageFromCourse(course: Course): CoursePageDocument {
  return {
    subtitle: course.subtitle,
    level: course.level,
    estimatedHours: course.estimatedHours,
    catalogSkills: course.catalogSkills,
    curriculumLead: course.curriculumLead,
    problem: course.problem,
    outcomes: course.outcomes,
    inside: course.inside,
    handsOn: course.handsOn,
    highlights: course.highlights,
    audience: course.audience,
    assessment: course.assessment,
    enrollCta: course.enrollCta,
  }
}
