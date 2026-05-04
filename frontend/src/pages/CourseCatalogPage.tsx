import { useEffect, useState } from 'react'
import { listCourses, type Course } from '../lib/api'

/** Student catalog "Teach" CTA — teacher SPA is a separate origin (not /instructor on student routes). */
const teacherSiteBaseUrl =
  typeof import.meta.env.VITE_TEACHER_SITE_URL === 'string' && import.meta.env.VITE_TEACHER_SITE_URL.trim().length > 0
    ? import.meta.env.VITE_TEACHER_SITE_URL.trim().replace(/\/$/, '')
    : 'https://teach.streammycourse.com'
import { CourseCard } from '../components/course/CourseCard'
import { CourseGrid } from '../components/course/CourseGrid'
import { CourseSkeleton } from '../components/course/CourseSkeleton'

export default function CourseCatalogPage() {
  const [courses, setCourses] = useState<Course[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function run() {
      try {
        const data = await listCourses()
        if (!cancelled) setCourses(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load courses')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void run()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-7 sm:space-y-10">
      {/* Hero — wider rhythm, deeper panel */}
      <section className="overflow-hidden rounded-2xl border border-slate-600/40 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950/90 text-white shadow-xl shadow-slate-900/20 ring-1 ring-white/10 lg:rounded-3xl">
        <div className="px-5 py-14 sm:px-8 sm:py-16 lg:px-12 lg:py-24">
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-x-16 xl:gap-x-20">
            <div className="min-w-0">
              <h1 className="text-4xl font-bold leading-[1.12] tracking-tight sm:text-5xl lg:text-[2.75rem] xl:text-6xl">
                Online courses taught by working instructors
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-300 sm:text-xl">
                Practical video training you can stream anytime. Learn real skills, follow structured lessons,
                and start free — every course on StreamMyCourse is free during the MVP.
              </p>
              <div className="mt-10 flex flex-wrap gap-4">
                <a
                  href="#courses"
                  className="inline-flex items-center justify-center rounded-md bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-100"
                >
                  Browse courses
                </a>
                <a
                  href={teacherSiteBaseUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center rounded-md border border-slate-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700/80"
                >
                  Teach on StreamMyCourse
                </a>
              </div>
            </div>
            <div className="flex min-w-0 justify-center lg:justify-end">
              <div className="aspect-[4/5] w-full max-w-sm overflow-hidden rounded-2xl border border-slate-400/30 bg-slate-900/80 shadow-2xl shadow-black/25 ring-1 ring-white/15 lg:max-w-md xl:max-w-lg">
                <img
                  src="/hero-lab-coat.png"
                  alt="Instructor in a lab coat"
                  className="h-full w-full object-cover object-top"
                  width={400}
                  height={500}
                  decoding="async"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="courses"
        className="scroll-mt-20 rounded-2xl border border-slate-200/70 bg-gradient-to-b from-white via-slate-50/90 to-white px-6 py-12 shadow-lg shadow-slate-400/12 ring-1 ring-white/80 sm:px-10 sm:py-16 lg:rounded-3xl"
      >
          {error && (
            <div className="mb-8 rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex">
                <svg className="mt-0.5 h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error loading courses</h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 sm:text-3xl">On-demand courses</h2>
            <p className="mt-1 text-slate-600">Click a course to view lessons and start learning.</p>
          </div>

          {loading && (
            <CourseGrid>
              <CourseSkeleton />
              <CourseSkeleton />
              <CourseSkeleton />
            </CourseGrid>
          )}

          {!loading && !error && (
            <>
              {courses.length > 0 ? (
                <CourseGrid>
                  {courses.map((course) => (
                    <CourseCard key={course.id} course={course} />
                  ))}
                </CourseGrid>
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 py-16 text-center">
                  <h3 className="text-lg font-medium text-gray-900">No courses available</h3>
                  <p className="mt-2 text-gray-600">Check back later for new courses.</p>
                </div>
              )}
            </>
          )}
      </section>

      <section
        id="about"
        className="scroll-mt-20 rounded-2xl border border-slate-200/70 bg-gradient-to-b from-white via-indigo-50/30 to-slate-50/80 px-6 py-12 shadow-lg shadow-slate-400/10 ring-1 ring-white/80 sm:px-10 sm:py-14 lg:rounded-3xl"
      >
          <h2 className="text-2xl font-bold text-slate-900">About</h2>
          <p className="mt-4 max-w-3xl text-slate-600">
            StreamMyCourse is a lightweight video course platform for instructors who want to publish structured
            lessons and for learners who want a simple browse-to-watch experience — no accounts required in the MVP.
          </p>
      </section>

      <section
        id="contact"
        className="scroll-mt-20 rounded-2xl border border-slate-200/70 bg-gradient-to-b from-white via-slate-50/90 to-indigo-50/40 px-6 py-12 shadow-lg shadow-slate-400/10 ring-1 ring-white/80 sm:px-10 sm:py-14 lg:rounded-3xl"
      >
          <h2 className="text-2xl font-bold text-slate-900">Contact</h2>
          <p className="mt-4 max-w-3xl text-slate-600">
            Questions or pilot feedback? Reach out through your team channel or add a contact form here when you wire
            email support.
          </p>
      </section>
    </div>
  )
}
