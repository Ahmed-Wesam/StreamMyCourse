import { useEffect, useState } from 'react'

import { fetchMe } from '../../lib/api/session'
import { type LessonPlayerPrefs, resolveLessonPlayerPrefs } from '../../lib/lessonPlayerPrefs'

export function useLessonPlayerPrefs(): LessonPlayerPrefs {
  const [prefs, setPrefs] = useState<LessonPlayerPrefs>(() => resolveLessonPlayerPrefs(null))

  useEffect(() => {
    let cancelled = false
    void fetchMe()
      .then((profile) => {
        if (!cancelled) setPrefs(resolveLessonPlayerPrefs(profile))
      })
      .catch(() => {
        if (!cancelled) setPrefs(resolveLessonPlayerPrefs(null))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return prefs
}
