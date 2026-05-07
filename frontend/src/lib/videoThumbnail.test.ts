/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { captureFrameAtVideoPercent } from './videoThumbnail'

describe('captureFrameAtVideoPercent', () => {
  const origCreate = document.createElement.bind(document)
  let createObjectURLSpy: ReturnType<typeof vi.fn>
  let revokeObjectURLSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => 'blob:unit-test')
    revokeObjectURLSpy = vi.fn()
    Object.defineProperty(globalThis.URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: createObjectURLSpy,
    })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: revokeObjectURLSpy,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('rejects when video metadata fails and still revokes the object URL', async () => {
    const fakeVideo = {
      muted: false,
      playsInline: false,
      preload: '',
      src: '',
      setAttribute: vi.fn(),
      onloadedmetadata: null as null | (() => void),
      onerror: null as null | (() => void),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }
    Object.defineProperty(fakeVideo, 'src', {
      configurable: true,
      set() {
        queueMicrotask(() => {
          fakeVideo.onerror?.()
        })
      },
    })

    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'video') return fakeVideo as unknown as HTMLVideoElement
      return origCreate(tag)
    })

    const file = new File([], 'clip.mp4', { type: 'video/mp4' })
    await expect(captureFrameAtVideoPercent(file, 0.2)).rejects.toThrow(/Could not read video metadata/)
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:unit-test')
  })
})
