import type { RefObject, ReactNode } from 'react'

import type { Playback } from '../../lib/api/types'
import { VideoPlayer } from './VideoPlayer'

function formatMinutes(durationSec: number | undefined): string {
  if (!durationSec || durationSec <= 0) return ''
  const mins = Math.max(1, Math.round(durationSec / 60))
  return `${mins} minute${mins === 1 ? '' : 's'}`
}

type Props = {
  loading: boolean
  playback: Playback | null
  resumeTimeSec: number
  videoRef: RefObject<HTMLVideoElement | null>
  onS3LoadedMetadata: () => void
  onPlaybackProgress: (positionSec: number, durationSec: number) => void
  onPlaybackEnded: () => void
  onPlaybackPause: (positionSec: number) => void
  metaLabel?: string
  showPosterChrome?: boolean
  fallback?: ReactNode
}

export function LessonPlayerVideoArea({
  loading,
  playback,
  resumeTimeSec,
  videoRef,
  onS3LoadedMetadata,
  onPlaybackProgress,
  onPlaybackEnded,
  onPlaybackPause,
  metaLabel,
  showPosterChrome = true,
  fallback,
}: Props) {
  const posterVisible = showPosterChrome && (loading || !playback)

  return (
    <div className="vid-wrap" data-testid="lesson-player-video-wrap">
      {posterVisible ? (
        <div className="vid" aria-hidden={Boolean(playback && !loading)}>
          <div className={`vid-poster${playback && !loading ? ' is-hidden' : ''}`}>
            <div className="vid-play">
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <polygon points="7,5 19,12 7,19" />
              </svg>
            </div>
            {metaLabel ? (
              <div className="vp-meta">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                {metaLabel}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {loading ? (
        fallback ?? null
      ) : playback ? (
        <div className="video-player-host">
          <VideoPlayer
            playback={playback}
            resumeTimeSec={resumeTimeSec}
            videoRef={videoRef}
            onS3LoadedMetadata={onS3LoadedMetadata}
            onPlaybackProgress={onPlaybackProgress}
            onPlaybackEnded={onPlaybackEnded}
            onPlaybackPause={onPlaybackPause}
            className="h-full w-full"
          />
        </div>
      ) : null}
    </div>
  )
}

export function lessonVideoMetaLabel(
  activeModuleLabel: string,
  activeLessonTitle: string,
  durationSec: number | undefined,
): string {
  const duration = formatMinutes(durationSec)
  const parts = [activeModuleLabel, activeLessonTitle].filter(Boolean)
  const head = parts.length ? parts.join(' · ') : 'Lecture'
  return duration ? `${head} · ${duration}` : head
}
