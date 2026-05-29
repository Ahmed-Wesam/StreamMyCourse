import { Suspense, lazy, useRef, type RefObject, type SyntheticEvent } from 'react'
import type { EventTimeUpdateTypes } from '@kinescope/react-kinescope-player'

import { parseKinescopeTimePayload } from '../../lib/kinescopePlayback'
import { watermarkProfileIncompletePlaybackMessage } from '../../lib/apiUserMessages'
import type { Playback } from '../../lib/api/types'

const KinescopePlayer = lazy(() => import('@kinescope/react-kinescope-player'))

type Props = {
  playback: Playback | null
  resumeTimeSec?: number
  videoRef: RefObject<HTMLVideoElement | null>
  /** S3 only: metadata loaded (duration discovery + resume seek). */
  onS3LoadedMetadata?: () => void
  onPlaybackProgress: (positionSec: number, durationSec: number) => void
  onPlaybackEnded: () => void
  onPlaybackPause: (positionSec: number) => void
  className?: string
}

export function VideoPlayer({
  playback,
  resumeTimeSec = 0,
  videoRef,
  onS3LoadedMetadata,
  onPlaybackProgress,
  onPlaybackEnded,
  onPlaybackPause,
  className,
}: Props) {
  const lastKinescopePositionRef = useRef(0)

  if (!playback) {
    return null
  }

  if (playback.provider === 'kinescope') {
    const watermarkText = playback.watermarkText?.trim()
    if (!watermarkText) {
      return (
        <div className={className} role="alert">
          {watermarkProfileIncompletePlaybackMessage}
        </div>
      )
    }

    const seek = resumeTimeSec > 0 ? resumeTimeSec : undefined
    return (
      <Suspense
        fallback={
          <div className={className} aria-busy="true" aria-label="Loading video player" />
        }
      >
        <div className={className}>
          <KinescopePlayer
            videoId={playback.videoId}
            drmAuthToken={playback.drmAuthToken}
            width="100%"
            height="100%"
            className="h-full w-full"
            query={seek != null ? { seek } : undefined}
            watermark={{ text: watermarkText, mode: 'random' }}
            onTimeUpdate={(data: EventTimeUpdateTypes) => {
              const { positionSec, durationSec } = parseKinescopeTimePayload(data)
              lastKinescopePositionRef.current = positionSec
              onPlaybackProgress(positionSec, durationSec)
            }}
            onEnded={onPlaybackEnded}
            onPause={() => onPlaybackPause(lastKinescopePositionRef.current)}
          />
        </div>
      </Suspense>
    )
  }

  return (
    <video
      ref={videoRef}
      controls
      playsInline
      preload="metadata"
      crossOrigin="anonymous"
      className={className}
      src={playback.playbackUrl}
      onLoadedMetadata={onS3LoadedMetadata}
      onDurationChange={onS3LoadedMetadata}
      onCanPlay={onS3LoadedMetadata}
      onTimeUpdate={(e: SyntheticEvent<HTMLVideoElement>) => {
        const video = e.currentTarget
        const positionSec = Math.floor(video.currentTime)
        const durationSec =
          Number.isFinite(video.duration) && video.duration > 0 ? Math.floor(video.duration) : 0
        onPlaybackProgress(positionSec, durationSec)
      }}
      onEnded={onPlaybackEnded}
      onPause={(e: SyntheticEvent<HTMLVideoElement>) => {
        onPlaybackPause(Math.floor(e.currentTarget.currentTime))
      }}
    />
  )
}
