import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getCourse,
  getCourseProgress,
  listLessons,
  listCourseModules,
  updateLessonProgress,
} from '../lib/api/catalog'
import { hasSignedInIdToken } from '../lib/api/session'
import type { Course, CourseModule, CourseProgress, Lesson } from '../lib/api/types'
import { catalogApiUserMessage, courseNotFoundMessage } from '../lib/apiUserMessages'
import { usePageTitle } from '../lib/page-title'
import { courseDetailHeroTitle } from './course-detail/courseDetailHeroTitle'
import { CourseDetailView } from './course-detail/CourseDetailView'
import './CourseDetailPage.css'

export default function CourseDetailPage() {
  const params = useParams()
  const courseId = useMemo(() => params.courseId ?? '', [params.courseId])

  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [modules, setModules] = useState<CourseModule[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [previewOnly, setPreviewOnly] = useState(false)
  const [needsAccess, setNeedsAccess] = useState(false)
  const [courseProgress, setCourseProgress] = useState<CourseProgress | null>(null)
  const [markingLessonId, setMarkingLessonId] = useState<string | null>(null)

  usePageTitle(course?.title?.trim() || 'Course')

  const loadCourseData = useCallback(async () => {
    setError(null)
    setLoading(true)
    setCourse(null)
    setLessons([])
    setModules([])
    setCourseProgress(null)
    const signedIn = await hasSignedInIdToken()
    setPreviewOnly(!signedIn)
    setNeedsAccess(false)
    try {
      const [c, l, m] = await Promise.all([getCourse(courseId), listLessons(courseId), listCourseModules(courseId)])
      if (!c) {
        setCourse(null)
        setLessons([])
        setModules([])
        setError(courseNotFoundMessage)
        return
      }
      setCourse(c)
      setModules([...m].sort((a, b) => a.order - b.order))
      setLessons([...l].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order))
      if (signedIn) {
        setNeedsAccess((c.hasAccess ?? c.enrolled) === false)
      }
      if (signedIn) {
        try {
          const prog = await getCourseProgress(courseId)
          setCourseProgress(prog)
        } catch {
          setCourseProgress(null)
        }
      }
    } catch (e) {
      setError(catalogApiUserMessage(e, 'loadCourse'))
      setCourse(null)
      setLessons([])
      setModules([])
    } finally {
      setLoading(false)
    }
  }, [courseId])

  const onToggleLessonComplete = useCallback(
    (lesson: Lesson, nextCompleted: boolean) => {
      if (!courseId) return
      void (async () => {
        if (markingLessonId) return
        setMarkingLessonId(lesson.id)
        try {
          const res = await updateLessonProgress(courseId, lesson.id, {
            lastPositionSec: 0,
            durationSec: lesson.duration ?? 0,
            ...(nextCompleted ? { markComplete: true } : { markIncomplete: true }),
          })
          const updated = res.lessonProgress
          if (!updated) return
          setCourseProgress((prev) => {
            if (!prev) return prev
            const nextLessons = prev.lessons.map((p) =>
              p.lessonId === updated.lessonId
                ? {
                    ...p,
                    completed: updated.completed,
                    lastPositionSec: updated.lastPositionSec,
                    completedAt: updated.completedAt,
                  }
                : p,
            )
            const completedCount = nextLessons.filter((item) => item.completed).length
            const percentComplete =
              prev.totalReadyLessons > 0 ? Math.round((completedCount / prev.totalReadyLessons) * 10000) / 100 : 0
            return { ...prev, lessons: nextLessons, completedCount, percentComplete }
          })
        } catch {
          return
        } finally {
          setMarkingLessonId(null)
        }
      })()
    },
    [courseId, markingLessonId],
  )

  useEffect(() => {
    if (courseId) void loadCourseData()
  }, [courseId, loadCourseData])

  if (loading || error || !course) {
    const title = courseDetailHeroTitle(loading, course, error)
    return (
      <div className="pg-course">
        <section className="chero" aria-label="Course hero">
          <div className="wrap">
            <h1>{title}</h1>
            {loading ? <div className="animate-pulse" /> : null}
            {error ? <p className="sub">{error}</p> : null}
          </div>
        </section>
      </div>
    )
  }

  return (
    <CourseDetailView
      course={course}
      courseId={courseId}
      lessons={lessons}
      modules={modules}
      courseProgress={courseProgress}
      previewOnly={previewOnly}
      needsAccess={needsAccess}
      onToggleLessonComplete={onToggleLessonComplete}
      markingLessonId={markingLessonId}
    />
  )
}
