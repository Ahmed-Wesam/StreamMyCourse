import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listCourses, listLessons } from '../lib/api'
import { catalogApiUserMessage } from '../lib/apiUserMessages'

export default function LearnRedirectPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function run() {
      try {
        const courses = await listCourses()
        const first = courses[0]
        if (!first) {
          if (!cancelled) setError('No courses available yet.')
          return
        }
        const lessons = await listLessons(first.id)
        const lesson = lessons[0]
        if (!lesson) {
          if (!cancelled) setError('No lessons available yet.')
          return
        }
        navigate(`/courses/${first.id}/lessons/${lesson.id}`, { replace: true })
      } catch (e) {
        setError(catalogApiUserMessage(e, 'learnRedirect'))
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [navigate])

  return (
    <div className="min-h-[50vh] flex items-center justify-center px-6">
      <div className="max-w-md w-full bg-card border border-border rounded-xl p-6 text-center">
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <p className="text-sm text-muted-foreground">Loading your course…</p>
        )}
      </div>
    </div>
  )
}

