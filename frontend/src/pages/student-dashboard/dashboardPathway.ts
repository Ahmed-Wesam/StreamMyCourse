export type DashboardPathwayCourse = {
  courseId: string
  title: string
  certified: boolean
  href?: string
}

const PATHWAY_TITLES = [
  'Research Methodology',
  'Statistics & SPSS',
  'Scientific Writing',
  'Systematic Reviews & Meta-Analysis',
]

/** Prototype pathway names when the Research Team API has not returned courses. */
export function pathwayCoursesOrPrototype(courses: DashboardPathwayCourse[]): DashboardPathwayCourse[] {
  if (courses.length > 0) return courses
  return PATHWAY_TITLES.map((title) => ({ courseId: title, title, certified: false }))
}
