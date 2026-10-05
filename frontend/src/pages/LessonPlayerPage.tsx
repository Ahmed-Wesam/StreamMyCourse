import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from 'react'
import { Link, useNavigate, useParams, useSearchParams, type To } from 'react-router-dom'
import {
  getCourse,
  getCourseProgress,
  getPlaybackUrl,
  listLessons,
  listCourseModules,
  updateLessonProgress,
} from '../lib/api/catalog'
import {
  isCourseAccessDeniedError,
  isPlaybackAuthRequiredError,
  isSessionSupersededError,
} from '../lib/api/client'
import type {
  Course,
  CourseModule,
  CourseProgress,
  Lesson,
  Playback,
} from '../lib/api/types'
import {
  catalogApiUserMessage,
  courseNotFoundMessage,
  incompleteLessonPlayerLinkMessage,
} from '../lib/apiUserMessages'
import { resolveNextAccessibleLesson, resolvePrevAccessibleLesson } from '../lib/moduleGating'
import { usePageTitle } from '../lib/page-title'
import { useRevokeLessonPlaybackOnSessionSuperseded } from '../lib/use-revoke-lesson-playback-on-session-superseded'
import { readMdUpMatch, useIsMdUp } from '../lib/useMediaQuery'
import { LessonCompletionCelebration } from './lesson-player/LessonCompletionCelebration'
import { LessonPlayerMobileView } from './lesson-player/LessonPlayerMobileView'
import {
  CourseLessonsSidebar,
  resolveNextModuleQuizHref,
  resolvePrevModuleQuizHref,
  LessonPlaybackNavigation,
  LessonPlayerAlerts,
  LessonUpNextCard,
  sortLessonsByOrdering,
  sortModulesByOrder,
} from './lesson-player/lessonPlayerUi'
import { LessonPlayerTabs } from './lesson-player/LessonPlayerTabs'
import {
  LessonPlayerVideoArea,
  lessonVideoMetaLabel,
} from './lesson-player/LessonPlayerVideoArea'
import { useLessonPlayerPrefs } from './lesson-player/useLessonPlayerPrefs'
import './LessonPlayerPage.css'

function hrefToPath(href: To): string {
  if (typeof href === 'string') return href
  return `${href.pathname ?? ''}${href.search ?? ''}${href.hash ?? ''}`
}

function isModuleFullyComplete(
  moduleId: string,
  lessons: Lesson[],
  progress: CourseProgress | null,
): boolean {
  if (!moduleId || !progress) return false
  const inModule = lessons.filter((lesson) => lesson.moduleId === moduleId)
  if (inModule.length === 0) return false
  return inModule.every((lesson) => progress.lessons.find((row) => row.lessonId === lesson.id)?.completed)
}

// Progress tracking constants
const PROGRESS_INTERVAL_MS = 15000 // 15 seconds between heartbeat attempts
const MAX_CONSECUTIVE_FAILURES = 10 // Circuit breaker threshold
const MAX_SAME_POSITION_STREAK = 20 // Stop saving if timestamp doesn't change

function LessonPrimaryColumn({
  loading,
  playback,
  resumeTimeSec,
  videoRef,
  onS3LoadedMetadata,
  onPlaybackProgress,
  onPlaybackEnded,
  onPlaybackPause,
  activeLessonTitle,
  activeModuleLabel,
  isLessonCompleted,
  courseDescription,
  onMarkComplete,
  onMarkIncomplete,
  courseId,
  lessonId,
  moduleId,
  playbackPositionSec,
  contentTabsEnabled,
  prevLesson,
  prevQuizHref,
  nextLesson,
  nextQuizHref,
  playbackNavLocked,
  lessonTranscript,
  autoCompletePill,
  activeLessonDurationSec,
  transcriptFetchReady,
}: {
  loading: boolean
  playback: Playback | null
  resumeTimeSec: number
  videoRef: RefObject<HTMLVideoElement | null>
  onS3LoadedMetadata: () => void
  onPlaybackProgress: (positionSec: number, durationSec: number) => void
  onPlaybackEnded: () => void
  onPlaybackPause: (positionSec: number) => void
  activeLessonTitle: string
  activeModuleLabel: string
  isLessonCompleted: boolean
  courseDescription: string | undefined
  onMarkComplete: () => void
  onMarkIncomplete: () => void
  courseId: string
  lessonId: string
  moduleId?: string
  playbackPositionSec: number
  contentTabsEnabled: boolean
  prevLesson: Lesson | null
  prevQuizHref?: To | null
  nextLesson: Lesson | null
  nextQuizHref?: To | null
  playbackNavLocked: boolean
  lessonTranscript?: string
  autoCompletePill: boolean
  activeLessonDurationSec: number
  transcriptFetchReady: boolean
}) {
  const upNextTitle = nextQuizHref ? 'Module quiz' : nextLesson?.title
  const upNextHref = nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)
  const videoMeta = lessonVideoMetaLabel(activeModuleLabel, activeLessonTitle, activeLessonDurationSec)

  return (
    <>
      <LessonPlayerVideoArea
        loading={loading}
        playback={playback}
        resumeTimeSec={resumeTimeSec}
        videoRef={videoRef}
        onS3LoadedMetadata={onS3LoadedMetadata}
        onPlaybackProgress={onPlaybackProgress}
        onPlaybackEnded={onPlaybackEnded}
        onPlaybackPause={onPlaybackPause}
        metaLabel={videoMeta}
      />

      <div className="lec-meta">
        {activeModuleLabel ? (
          <span className="lec-tag">
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <polygon points="8,5 19,12 8,19" />
            </svg>
            {activeModuleLabel}
          </span>
        ) : null}
        <h1>{activeLessonTitle}</h1>
        <div className="lec-pills">
          {activeLessonDurationSec > 0 ? (
            <span className="lec-pill">{Math.max(1, Math.round(activeLessonDurationSec / 60))} min</span>
          ) : null}
          <span className="lec-pill">Video lesson</span>
          {autoCompletePill ? (
            <span className="lec-pill auto">Auto-completes when finished</span>
          ) : null}
        </div>
        <div className="lec-actions">
          <button
            type="button"
            disabled={loading || playbackNavLocked}
            onClick={isLessonCompleted ? onMarkIncomplete : onMarkComplete}
            className={`btn-complete${isLessonCompleted ? ' is-done' : ''}`}
          >
            {isLessonCompleted ? 'Mark as Incomplete' : 'Mark as Complete'}
          </button>
        </div>
      </div>

      {upNextTitle && upNextHref ? (
        <div className="up-next">
          <div className="un-info">
            <span className="un-label">Up Next</span>
            <h3>{upNextTitle}</h3>
          </div>
          {playbackNavLocked ? (
            <span className="btn-white is-disabled" aria-disabled="true">
              Start Next Lecture
            </span>
          ) : (
            <Link to={upNextHref} className="btn-white">
              Start Next Lecture
            </Link>
          )}
        </div>
      ) : upNextTitle ? (
        <LessonUpNextCard
          upNextTitle={upNextTitle}
          upNextDescription="Continue to the next lesson"
          playbackNavLocked={playbackNavLocked}
        />
      ) : null}

      <LessonPlayerTabs
        courseId={courseId}
        lessonId={lessonId}
        moduleId={moduleId}
        courseDescription={courseDescription}
        activeModuleLabel={activeModuleLabel}
        activeLessonTitle={activeLessonTitle}
        playbackPositionSec={playbackPositionSec}
        contentEnabled={contentTabsEnabled}
        lessonTranscriptFromList={lessonTranscript}
        transcriptFetchReady={transcriptFetchReady}
        prototypeShell
      />

      <LessonPlaybackNavigation
        courseId={courseId}
        playbackNavLocked={playbackNavLocked}
        prevLesson={prevLesson}
        prevQuizHref={prevQuizHref}
        nextLesson={nextLesson}
        nextQuizHref={nextQuizHref}
      />
    </>
  )
}


export default function LessonPlayerPage() {
  usePageTitle('Lesson')
  const navigate = useNavigate()
  const playerPrefs = useLessonPlayerPrefs()
  const params = useParams()
  const [searchParams] = useSearchParams()
  const courseId = useMemo(() => params.courseId ?? '', [params.courseId])
  const lessonId = useMemo(() => params.lessonId ?? '', [params.lessonId])
  // Resume time from URL (?t=123) - saved position passed from CourseDetailPage
  const resumeTimeSec = useMemo(() => {
    const t = searchParams.get('t')
    if (!t) return null
    const parsed = parseInt(t, 10)
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null
  }, [searchParams])

  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [modules, setModules] = useState<CourseModule[]>([])
  const [playback, setPlayback] = useState<Playback | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsSubscription, setNeedsSubscription] = useState(false)
  const [needsSignIn, setNeedsSignIn] = useState(false)
  const [courseProgress, setCourseProgress] = useState<CourseProgress | null>(null)
  const lastAttemptRef = useRef<number>(0) // Track last attempt time (initialized to 0 to allow first update)
  const consecutiveFailuresRef = useRef<number>(0)
  const circuitOpenRef = useRef<boolean>(false)
  const lastSentPositionSecRef = useRef<number | null>(null)
  const samePositionStreakRef = useRef<number>(0)
  const samePositionCircuitOpenRef = useRef<boolean>(false)
  const inFlightProgressRef = useRef<Promise<unknown> | null>(null)
  const isUnmountedRef = useRef<boolean>(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  // Track if we've applied the initial resume time to prevent re-seeking
  const resumeAppliedRef = useRef<boolean>(false)
  // Track if we've sent duration update to prevent duplicate calls (S3 path only)
  const durationSentRef = useRef<boolean>(false)
  const lastPlaybackPositionRef = useRef(0)
  const lastPlaybackDurationRef = useRef(0)
  const [playbackPositionSec, setPlaybackPositionSec] = useState(0)
  const [celebration, setCelebration] = useState<{ title: string; subtitle: string } | null>(null)

  const playbackNavLocked = needsSubscription || needsSignIn
  const guardedPlayback = playbackNavLocked ? null : playback

  const revokePlaybackAccess = useCallback(() => {
    setPlayback(null)
    setNeedsSignIn(true)
    setNeedsSubscription(false)
    const video = videoRef.current
    if (video) {
      video.pause()
      video.removeAttribute('src')
      video.load()
    }
  }, [])

  useRevokeLessonPlaybackOnSessionSuperseded(revokePlaybackAccess)

  useEffect(() => {
    return () => {
      isUnmountedRef.current = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setError(null)
    setCourse(null)
    setLessons([])
    setModules([])
    setPlayback(null)
    setCourseProgress(null)
    setNeedsSubscription(false)
    setNeedsSignIn(false)

    async function run() {
      try {
        const c = await getCourse(courseId)
        if (cancelled) return
        if (!c) {
          setError(courseNotFoundMessage)
          setCourse(null)
          setLessons([])
          setModules([])
          return
        }
        setCourse(c)
        const [l, m] = await Promise.all([listLessons(courseId), listCourseModules(courseId)])
        if (cancelled) return
        setModules(sortModulesByOrder(m))
        setLessons(sortLessonsByOrdering(l))
        try {
          const progressPromise = getCourseProgress(courseId).then(
            (prog) => ({ ok: true as const, prog }),
            () => ({ ok: false as const }),
          )
          const pb = await getPlaybackUrl(courseId, lessonId)
          if (cancelled) return
          setPlayback(pb)
          void progressPromise.then((progResult) => {
            if (!cancelled && progResult.ok) {
              setCourseProgress(progResult.prog)
            }
          })
        } catch (inner) {
          if (cancelled) return
          if (isCourseAccessDeniedError(inner)) {
            setNeedsSubscription(true)
            setPlayback(null)
            setError(null)
            setCourseProgress(null)
          } else if (isPlaybackAuthRequiredError(inner) || isSessionSupersededError(inner)) {
            setNeedsSignIn(true)
            setPlayback(null)
            setError(null)
            setCourseProgress(null)
          } else {
            setCourseProgress(null)
            setError(catalogApiUserMessage(inner, 'loadLesson'))
          }
        }
      } catch (e) {
        if (cancelled) return
        setError(catalogApiUserMessage(e, 'loadLesson'))
        setCourse(null)
        setPlayback(null)
        setLessons([])
        setModules([])
        setCourseProgress(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    if (!courseId || !lessonId) {
      setLoading(false)
      setError(incompleteLessonPlayerLinkMessage)
      return
    }

    void run()

    return () => {
      cancelled = true
    }
  }, [courseId, lessonId])

  const activeLessonTitle = useMemo(() => {
    const l = lessons.find((x) => x.id === lessonId)
    return l?.title ?? 'Lesson'
  }, [lessons, lessonId])

  const activeModuleLabel = useMemo(() => {
    const activeLesson = lessons.find((x) => x.id === lessonId)
    if (!activeLesson) return ''
    const mod = modules.find((m) => m.id === activeLesson.moduleId)
    if (!mod) return ''
    return mod.title
  }, [lessons, lessonId, modules])

  const activeModuleId = useMemo(() => {
    const activeLesson = lessons.find((x) => x.id === lessonId)
    return activeLesson?.moduleId ?? ''
  }, [lessons, lessonId])

  const activeLesson = useMemo(() => lessons.find((x) => x.id === lessonId), [lessons, lessonId])

  const activeLessonTranscript = useMemo(() => {
    if (!activeLesson) return undefined
    return activeLesson.transcript?.trim() ?? ''
  }, [activeLesson])

  const maybeCelebrateModule = useCallback(
    (progress: CourseProgress | null) => {
      if (!playerPrefs.progressCelebrations || !progress) return
      if (!isModuleFullyComplete(activeModuleId, lessons, progress)) return
      const mod = modules.find((m) => m.id === activeModuleId)
      setCelebration({
        title: `${mod?.title ?? 'Module'} complete`,
        subtitle: 'Nice work — continue to the next lectures when you are ready.',
      })
    },
    [activeModuleId, lessons, modules, playerPrefs.progressCelebrations],
  )

  const activeLessonIndex = useMemo(() => {
    return lessons.findIndex((x) => x.id === lessonId)
  }, [lessons, lessonId])

  const nextLesson = useMemo(
    () => resolveNextAccessibleLesson(lessons, activeLessonIndex, modules),
    [lessons, activeLessonIndex, modules],
  )

  const prevLesson = useMemo(
    () => resolvePrevAccessibleLesson(lessons, activeLessonIndex, modules),
    [lessons, activeLessonIndex, modules],
  )

  const nextQuizHref = useMemo(
    () =>
      resolveNextModuleQuizHref({
        courseId,
        lessonId,
        lessons,
        modules,
        playbackNavLocked,
      }),
    [courseId, lessonId, lessons, modules, playbackNavLocked],
  )

  const prevQuizHref = useMemo(
    () =>
      resolvePrevModuleQuizHref({
        courseId,
        lessonId,
        lessons,
        modules,
        playbackNavLocked,
      }),
    [courseId, lessonId, lessons, modules, playbackNavLocked],
  )

  const maybeAutoplayNext = useCallback(() => {
    if (!playerPrefs.autoplayNext || playbackNavLocked) return
    const href = nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)
    if (href) navigate(hrefToPath(href))
  }, [courseId, navigate, nextLesson, nextQuizHref, playbackNavLocked, playerPrefs.autoplayNext])

  const isLessonCompleted = useMemo(() => {
    const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lessonId)
    return lessonProgress?.completed ?? false
  }, [courseProgress, lessonId])

  // Calculate the best resume time from URL param or saved progress
  const getResumeTimeSec = useCallback((): number => {
    // Prioritize URL param (passed from CourseDetailPage)
    if (resumeTimeSec != null && resumeTimeSec > 0) {
      return resumeTimeSec
    }
    // Fall back to saved progress from API
    const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lessonId)
    const savedPosition = lessonProgress?.lastPositionSec ?? 0
    return savedPosition > 0 ? savedPosition : 0
  }, [resumeTimeSec, courseProgress, lessonId])

  const applyResumeSeek = useCallback(() => {
    const video = videoRef.current
    if (!video || resumeAppliedRef.current) return
    if (video.readyState < HTMLMediaElement.HAVE_METADATA) return

    const resumeTime = getResumeTimeSec()
    if (resumeTime <= 0) return

    const activeLesson = lessons.find((l) => l.id === lessonId)
    const catalogDuration = activeLesson?.duration ?? 0
    const mediaDuration = video.duration
    const effectiveDuration =
      Number.isFinite(mediaDuration) && mediaDuration > 0
        ? mediaDuration
        : catalogDuration > 0
          ? catalogDuration
          : 0
    if (effectiveDuration > 0 && resumeTime >= effectiveDuration) return

    video.currentTime = resumeTime
    resumeAppliedRef.current = true
  }, [getResumeTimeSec, lessonId, lessons])

  // Handle S3 metadata loaded — resume seek + client-side duration discovery for S3 uploads.
  const handleS3LoadedMetadata = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    // Send video duration to backend if we have a valid duration
    // This helps populate lesson duration for newly uploaded videos
    const videoDuration = Math.floor(video.duration)
    const activeLesson = lessons.find((l) => l.id === lessonId)
    const hasDuration = activeLesson?.duration && activeLesson.duration > 0

    if (videoDuration > 0 && !hasDuration && !durationSentRef.current) {
      // Mark as sent immediately to prevent duplicate calls
      durationSentRef.current = true
      // Send duration update (best effort - don't block playback on this)
      void updateLessonProgress(courseId, lessonId, {
        lastPositionSec: getResumeTimeSec(),
        durationSec: videoDuration,
      }).catch(() => {
        // Silently ignore - duration update is best effort
      })
    }

    applyResumeSeek()
  }, [applyResumeSeek, courseId, lessonId, lessons, getResumeTimeSec])

  // Resume when saved progress arrives after the video element already loaded metadata.
  useEffect(() => {
    applyResumeSeek()
  }, [applyResumeSeek, courseProgress, playback])

  // Reset flags when lesson changes
  useEffect(() => {
    resumeAppliedRef.current = false
    durationSentRef.current = false
    lastPlaybackPositionRef.current = 0
    lastPlaybackDurationRef.current = 0
    setPlaybackPositionSec(0)
  }, [lessonId])

  const effectiveLessonDurationSec = useCallback((): number => {
    const activeLesson = lessons.find((l) => l.id === lessonId)
    const fromLesson = activeLesson?.duration ?? 0
    if (fromLesson > 0) return fromLesson
    if (lastPlaybackDurationRef.current > 0) {
      return Math.ceil(lastPlaybackDurationRef.current)
    }
    const fromVideo = videoRef.current ? Math.floor(videoRef.current.duration) : 0
    return fromVideo > 0 ? fromVideo : 0
  }, [lessons, lessonId])

  const playbackResumeTimeSec = useMemo(() => getResumeTimeSec(), [getResumeTimeSec])

  // Helper to track and limit repeated saves at the same timestamp (e.g., user paused for hours)
  const shouldSkipBecauseSamePosition = (positionSec: number): boolean => {
    // If position changed, reset streak + close same-position circuit
    if (lastSentPositionSecRef.current === null || lastSentPositionSecRef.current !== positionSec) {
      lastSentPositionSecRef.current = positionSec
      samePositionStreakRef.current = 0
      samePositionCircuitOpenRef.current = false
      return false
    }

    // Position unchanged
    samePositionStreakRef.current += 1
    if (samePositionStreakRef.current >= MAX_SAME_POSITION_STREAK) {
      samePositionCircuitOpenRef.current = true
      return true
    }

    return false
  }

  const reportPlaybackProgress = useCallback(
    (positionSec: number, durationFromPlayer: number) => {
      lastPlaybackPositionRef.current = positionSec
      setPlaybackPositionSec(Math.max(0, Math.floor(positionSec)))
      if (durationFromPlayer > 0) {
        lastPlaybackDurationRef.current = durationFromPlayer
      }
      const now = Date.now()

      if (circuitOpenRef.current) return

      if (samePositionCircuitOpenRef.current && lastSentPositionSecRef.current === positionSec) return

      if (now - lastAttemptRef.current < PROGRESS_INTERVAL_MS) return

      if (inFlightProgressRef.current) return

      const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lessonId)
      if (lessonProgress?.completed) return

      const activeLesson = lessons.find((l) => l.id === lessonId)
      const lessonDuration = activeLesson?.duration ?? 0
      const durationSec =
        lessonDuration > 0
          ? lessonDuration
          : durationFromPlayer > 0
            ? durationFromPlayer
            : 0

      lastAttemptRef.current = now

      if (shouldSkipBecauseSamePosition(positionSec)) return

      const promise = updateLessonProgress(courseId, lessonId, {
        lastPositionSec: positionSec,
        durationSec,
      })
      inFlightProgressRef.current = promise
      promise
        .then(() => {
          if (!isUnmountedRef.current) {
            consecutiveFailuresRef.current = 0
          }
        })
        .catch(() => {
          consecutiveFailuresRef.current++
          if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
            circuitOpenRef.current = true
          }
        })
        .finally(() => {
          inFlightProgressRef.current = null
        })
    },
    [courseId, lessonId, lessons, courseProgress],
  )

  const handleVideoEnded = async () => {
    const lessonRow = lessons.find((l) => l.id === lessonId)
    if (!lessonRow) return

    const durationSec = effectiveLessonDurationSec()
    const positionSec = durationSec > 0 ? durationSec : currentPlaybackPositionSec()

    if (circuitOpenRef.current) return

    if (inFlightProgressRef.current) {
      await inFlightProgressRef.current.catch(() => {})
    }

    try {
      if (playerPrefs.autoMarkComplete) {
        await updateLessonProgress(courseId, lessonId, {
          lastPositionSec: positionSec,
          durationSec,
          markComplete: true,
        })
      } else {
        await updateLessonProgress(courseId, lessonId, {
          lastPositionSec: positionSec,
          durationSec,
        })
      }
      consecutiveFailuresRef.current = 0
      const prog = await getCourseProgress(courseId)
      if (!isUnmountedRef.current) {
        setCourseProgress(prog)
        maybeCelebrateModule(prog)
      }
      maybeAutoplayNext()
    } catch {
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }

  const handleMarkComplete = async () => {
    // Circuit breaker check
    if (circuitOpenRef.current) return

    const activeLesson = lessons.find((l) => l.id === lessonId)
    if (!activeLesson) return

    const durationSec = effectiveLessonDurationSec()

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: durationSec > 0 ? durationSec : currentPlaybackPositionSec(),
        durationSec,
        markComplete: true,
      })
      consecutiveFailuresRef.current = 0
      // Optimistically reflect completion in UI immediately; refetch below is source of truth.
      setCourseProgress((prev) => {
        if (!prev) {
          const totalReadyLessons = lessons.length
          const completedCount = 1
          const percentComplete =
            totalReadyLessons > 0 ? Math.round((completedCount / totalReadyLessons) * 100) : 0
          return {
            courseId,
            totalReadyLessons,
            completedCount,
            percentComplete,
            lessons: lessons.map((l) => ({
              lessonId: l.id,
              completed: l.id === lessonId,
              lastPositionSec: l.id === lessonId ? (activeLesson.duration || 0) : 0,
            })),
          }
        }
        const nextLessons = prev.lessons.map((l) =>
          l.lessonId === lessonId ? { ...l, completed: true } : l,
        )
        const wasCompleted = prev.lessons.find((l) => l.lessonId === lessonId)?.completed ?? false
        const completedCount = wasCompleted ? prev.completedCount : prev.completedCount + 1
        const total = prev.totalReadyLessons > 0 ? prev.totalReadyLessons : nextLessons.length
        const percentComplete = total > 0 ? Math.round((completedCount / total) * 100) : prev.percentComplete
        return { ...prev, lessons: nextLessons, completedCount, percentComplete }
      })
      const prog = await getCourseProgress(courseId)
      if (!isUnmountedRef.current) {
        // Some backends are eventually consistent; keep the lesson marked complete if we've just done so.
        const existing = prog.lessons.find((l) => l.lessonId === lessonId)
        const ensuredLessons =
          existing == null
            ? [
                ...prog.lessons,
                { lessonId, completed: true, lastPositionSec: activeLesson.duration || 0 },
              ]
            : existing.completed
              ? prog.lessons
              : prog.lessons.map((l) =>
                  l.lessonId === lessonId ? { ...l, completed: true } : l,
                )
        const ensuredCompletedCount = Math.max(
          prog.completedCount,
          ensuredLessons.filter((l) => l.completed).length,
        )
        const total = prog.totalReadyLessons > 0 ? prog.totalReadyLessons : ensuredLessons.length
        const ensuredPercent = total > 0 ? Math.round((ensuredCompletedCount / total) * 100) : prog.percentComplete
        const merged = {
          ...prog,
          lessons: ensuredLessons,
          completedCount: ensuredCompletedCount,
          percentComplete: ensuredPercent,
        }
        setCourseProgress(merged)
        maybeCelebrateModule(merged)
      }
    } catch {
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }

  const handleMarkIncomplete = async () => {
    // Circuit breaker check
    if (circuitOpenRef.current) return

    const activeLesson = lessons.find((l) => l.id === lessonId)

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: 0,
        durationSec: activeLesson?.duration ?? 0,
        markIncomplete: true,
      })
      // Reset failure count on success
      consecutiveFailuresRef.current = 0
      const prog = await getCourseProgress(courseId)
      setCourseProgress(prog)
    } catch {
      // Count failures and trip circuit breaker if needed
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }

  // Checkpoint save helper (ignores throttle, respects circuit breaker)
  const saveCheckpoint = useCallback(async (positionSec: number) => {
    if (circuitOpenRef.current) return
    if (!courseId || !lessonId) return

    // Check same-position circuit breaker: prevents spam when user pauses and leaves
    // tab open for hours. After 20 saves at the same timestamp, we stop until
    // the position changes (user resumes playback).
    if (shouldSkipBecauseSamePosition(positionSec)) return

    const durationSec = effectiveLessonDurationSec()

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: positionSec,
        durationSec,
      })
      consecutiveFailuresRef.current = 0
    } catch {
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }, [courseId, lessonId, effectiveLessonDurationSec])

  const handlePlaybackPause = useCallback(
    (positionSec: number) => {
      saveCheckpoint(positionSec)
    },
    [saveCheckpoint],
  )

  const currentPlaybackPositionSec = useCallback((): number => {
    const fromVideo = videoRef.current ? Math.floor(videoRef.current.currentTime) : 0
    return fromVideo > 0 ? fromVideo : lastPlaybackPositionRef.current
  }, [])

  const handleVisibilityChange = useCallback(() => {
    if (document.hidden) {
      saveCheckpoint(currentPlaybackPositionSec())
    }
  }, [saveCheckpoint, currentPlaybackPositionSec])

  const handlePageHide = useCallback(() => {
    if (circuitOpenRef.current) return
    saveCheckpoint(currentPlaybackPositionSec())
  }, [saveCheckpoint, currentPlaybackPositionSec])

  // Checkpoint event listeners
  useEffect(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('pagehide', handlePageHide)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('pagehide', handlePageHide)
    }
  }, [handleVisibilityChange, handlePageHide])

  const isMdUp = useIsMdUp()
  const [sidebarOpen, setSidebarOpen] = useState(readMdUpMatch)
  const desktopSidebarDismissedRef = useRef(false)
  const prevHeaderHref =
    prevQuizHref ?? (prevLesson ? `/courses/${courseId}/lessons/${prevLesson.id}` : null)
  const nextHeaderHref = nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)

  useEffect(() => {
    if (isMdUp && !desktopSidebarDismissedRef.current) {
      setSidebarOpen(true)
    }
  }, [isMdUp])

  const openDesktopSidebar = useCallback(() => {
    desktopSidebarDismissedRef.current = false
    setSidebarOpen(true)
  }, [])

  const closeDesktopSidebar = useCallback(() => {
    desktopSidebarDismissedRef.current = true
    setSidebarOpen(false)
  }, [])

  if (!isMdUp) {
    return (
      <div className="pg-lesson-player" data-testid="student-page-lesson-player">
      <LessonPlayerMobileView
        prefs={playerPrefs}
        lessonTranscript={activeLessonTranscript}
        activeLessonDurationSec={activeLesson?.duration ?? 0}
        courseId={courseId}
        lessons={lessons}
        modules={modules}
        lessonId={lessonId}
        moduleId={activeModuleId}
        activeLessonTitle={activeLessonTitle}
        activeModuleLabel={activeModuleLabel}
        loading={loading}
        playback={guardedPlayback}
        resumeTimeSec={playbackResumeTimeSec}
        videoRef={videoRef}
        onS3LoadedMetadata={handleS3LoadedMetadata}
        onPlaybackProgress={reportPlaybackProgress}
        onPlaybackEnded={handleVideoEnded}
        onPlaybackPause={handlePlaybackPause}
        needsSignIn={needsSignIn}
        needsSubscription={needsSubscription}
        error={error}
        playbackNavLocked={playbackNavLocked}
        courseProgress={courseProgress}
        courseDescription={course?.description}
        isLessonCompleted={isLessonCompleted}
        onMarkComplete={() => void handleMarkComplete()}
        onMarkIncomplete={() => void handleMarkIncomplete()}
        prevLesson={prevLesson}
        prevQuizHref={prevQuizHref}
        nextLesson={nextLesson}
        nextQuizHref={nextQuizHref}
        playbackPositionSec={playbackPositionSec}
        contentTabsEnabled={!playbackNavLocked}
      />
      <LessonCompletionCelebration
        open={celebration != null}
        title={celebration?.title ?? ''}
        subtitle={celebration?.subtitle ?? ''}
        onClose={() => setCelebration(null)}
      />
      </div>
    )
  }

  return (
    <div className="pg-lesson-player" data-testid="student-page-lesson-player">
      <header className="player-top">
        <div className="pt-wrap">
          {!sidebarOpen ? (
            <button
              type="button"
              onClick={openDesktopSidebar}
              className="pt-back"
              aria-label="Show sidebar"
              title="Show sidebar"
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          ) : (
            <Link to={`/courses/${courseId}`} className="pt-back" aria-label="Back to course">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M15 18l-6-6 6-6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </Link>
          )}

          <div className="pt-course">
            <p className="pt-name">{course?.title ?? activeLessonTitle}</p>
            {courseProgress != null ? (
              <div className="pt-meta">
                <div className="pt-bar">
                  <i style={{ width: `${courseProgress.percentComplete}%` }} />
                </div>
                <span className="pt-pct">{courseProgress.percentComplete}%</span>
              </div>
            ) : null}
          </div>

          <div className="pt-nav">
            {prevHeaderHref ? (
              playbackNavLocked ? (
                <span className="btn-nav is-disabled">Prev</span>
              ) : (
                <Link to={prevHeaderHref} className="btn-nav">
                  Prev
                </Link>
              )
            ) : null}
            {nextHeaderHref ? (
              playbackNavLocked ? (
                <span className="btn-nav primary is-disabled">Next</span>
              ) : (
                <Link to={nextHeaderHref} className="btn-nav primary">
                  Next
                </Link>
              )
            ) : null}
          </div>
        </div>
      </header>

      <div
        className={`player${sidebarOpen ? ' sidebar-open' : ''}`}
        style={{ gridTemplateColumns: sidebarOpen ? '340px 1fr' : '1fr' }}
      >
        <CourseLessonsSidebar
          error={error}
          lessons={lessons}
          modules={modules}
          courseId={courseId}
          activeLessonId={lessonId}
          playbackNavLocked={playbackNavLocked}
          courseProgress={courseProgress}
          sidebarOpen={sidebarOpen}
          onClose={closeDesktopSidebar}
          outerClassName="ps"
        />

        <section className="pm">
        <LessonPlayerAlerts
          needsSignIn={needsSignIn}
          needsSubscription={needsSubscription}
          error={error}
          courseId={courseId}
          compact
        />

        <LessonPrimaryColumn
          loading={loading}
          playback={guardedPlayback}
          resumeTimeSec={playbackResumeTimeSec}
          videoRef={videoRef}
          onS3LoadedMetadata={handleS3LoadedMetadata}
          onPlaybackProgress={reportPlaybackProgress}
          onPlaybackEnded={() => void handleVideoEnded()}
          onPlaybackPause={handlePlaybackPause}
          activeLessonTitle={activeLessonTitle}
          activeModuleLabel={activeModuleLabel}
          isLessonCompleted={isLessonCompleted}
          courseDescription={course?.description}
          onMarkComplete={() => void handleMarkComplete()}
          onMarkIncomplete={() => void handleMarkIncomplete()}
          courseId={courseId}
          lessonId={lessonId}
          moduleId={activeModuleId}
          playbackPositionSec={playbackPositionSec}
          contentTabsEnabled={!playbackNavLocked}
          prevLesson={prevLesson}
          prevQuizHref={prevQuizHref}
          nextLesson={nextLesson}
          nextQuizHref={nextQuizHref}
          playbackNavLocked={playbackNavLocked}
          lessonTranscript={activeLessonTranscript}
          autoCompletePill={playerPrefs.autoMarkComplete}
          activeLessonDurationSec={activeLesson?.duration ?? 0}
          transcriptFetchReady={!loading && Boolean(activeLesson)}
        />
        </section>
      </div>
    <LessonCompletionCelebration
      open={celebration != null}
      title={celebration?.title ?? ''}
      subtitle={celebration?.subtitle ?? ''}
      onClose={() => setCelebration(null)}
    />
    </div>
  )
}
