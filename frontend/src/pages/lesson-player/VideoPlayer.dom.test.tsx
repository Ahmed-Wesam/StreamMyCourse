/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import type { Playback } from '../../lib/api/types'
import { VideoPlayer } from './VideoPlayer'

type KinescopePlayerMockProps = {
  width?: string
  height?: string
  className?: string
  videoId: string
  watermark?: { text: string; mode: string }
}

const kinescopePlayerLastProps: { current: KinescopePlayerMockProps | null } = {
  current: null,
}

vi.mock('@kinescope/react-kinescope-player', () => ({
  default: (props: KinescopePlayerMockProps) => {
    kinescopePlayerLastProps.current = props
    return (
      <div
        data-testid="kinescope-player"
        data-video-id={props.videoId}
        data-width={props.width ?? ''}
        data-height={props.height ?? ''}
        data-watermark-text={props.watermark?.text ?? ''}
        data-watermark-mode={props.watermark?.mode ?? ''}
        className={props.className ?? ''}
      />
    )
  },
}))

describe('VideoPlayer', () => {
  beforeEach(() => {
    kinescopePlayerLastProps.current = null
  })

  afterEach(() => {
    cleanup()
  })

  it('wraps Kinescope player in aspect-video shell with full-size embed props', async () => {
    const playback: Playback = {
      provider: 'kinescope',
      videoId: 'vid-123',
      drmAuthToken: 'jwt-token',
      watermarkText: 'Jane Doe\njane@gmail.com',
    }

    const { container } = render(
      <VideoPlayer
        playback={playback}
        videoRef={{ current: null }}
        onPlaybackProgress={() => {}}
        onPlaybackEnded={() => {}}
        onPlaybackPause={() => {}}
        className="aspect-video w-full"
      />,
    )

    const shell = container.querySelector('.aspect-video.w-full')
    expect(shell).not.toBeNull()

    const player = await screen.findByTestId('kinescope-player')
    expect(player.getAttribute('data-video-id')).toBe('vid-123')
    expect(player.getAttribute('data-width')).toBe('100%')
    expect(player.getAttribute('data-height')).toBe('100%')
    expect(player.className).toContain('h-full')
    expect(player.className).toContain('w-full')
  })

  it('passes watermark to Kinescope player when playback includes watermarkText', async () => {
    const playback: Playback = {
      provider: 'kinescope',
      videoId: 'vid-123',
      drmAuthToken: 'jwt-token',
      watermarkText: 'Jane Doe\njane@gmail.com',
    }

    render(
      <VideoPlayer
        playback={playback}
        videoRef={{ current: null }}
        onPlaybackProgress={() => {}}
        onPlaybackEnded={() => {}}
        onPlaybackPause={() => {}}
        className="aspect-video w-full"
      />,
    )

    await waitFor(() => {
      expect(kinescopePlayerLastProps.current?.watermark).toEqual({
        text: 'Jane Doe\njane@gmail.com',
        mode: 'random',
      })
    })
  })

  it('shows profile message when kinescope playback lacks watermarkText', async () => {
    const playback: Playback = {
      provider: 'kinescope',
      videoId: 'vid-123',
      drmAuthToken: 'jwt-token',
      watermarkText: '',
    }

    render(
      <VideoPlayer
        playback={playback}
        videoRef={{ current: null }}
        onPlaybackProgress={() => {}}
        onPlaybackEnded={() => {}}
        onPlaybackPause={() => {}}
        className="aspect-video w-full"
      />,
    )

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByTestId('kinescope-player')).toBeNull()
  })

  it('shows profile message when playback watermarkText is whitespace only', async () => {
    const playback: Playback = {
      provider: 'kinescope',
      videoId: 'vid-123',
      drmAuthToken: 'jwt-token',
      watermarkText: '   ',
    }

    render(
      <VideoPlayer
        playback={playback}
        videoRef={{ current: null }}
        onPlaybackProgress={() => {}}
        onPlaybackEnded={() => {}}
        onPlaybackPause={() => {}}
        className="aspect-video w-full"
      />,
    )

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByTestId('kinescope-player')).toBeNull()
  })
})
