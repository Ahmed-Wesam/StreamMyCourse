/**
 * @vitest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Playback } from '../../lib/api/types'
import { VideoPlayer } from './VideoPlayer'

vi.mock('@kinescope/react-kinescope-player', () => ({
  default: (props: { width?: string; height?: string; className?: string; videoId: string }) => (
    <div
      data-testid="kinescope-player"
      data-video-id={props.videoId}
      data-width={props.width ?? ''}
      data-height={props.height ?? ''}
      className={props.className ?? ''}
    />
  ),
}))

describe('VideoPlayer', () => {
  it('wraps Kinescope player in aspect-video shell with full-size embed props', async () => {
    const playback: Playback = {
      provider: 'kinescope',
      videoId: 'vid-123',
      drmAuthToken: 'jwt-token',
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
})
