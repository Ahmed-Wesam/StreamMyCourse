/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const createLesson = vi.hoisted(() => vi.fn())
const getUploadUrl = vi.hoisted(() => vi.fn())
const markLessonVideoReady = vi.hoisted(() => vi.fn())
const captureFrameAtVideoPercent = vi.hoisted(() => vi.fn())

vi.mock('./api', () => ({
  createLesson: (...a: unknown[]) => createLesson(...a),
  getUploadUrl: (...a: unknown[]) => getUploadUrl(...a),
  markLessonVideoReady: (...a: unknown[]) => markLessonVideoReady(...a),
}))

vi.mock('./videoThumbnail', () => ({
  captureFrameAtVideoPercent: (...a: unknown[]) => captureFrameAtVideoPercent(...a),
}))

import { createAndUploadDraftLesson } from './courseManagementLessonUpload'

function xhrListeners() {
  const m = new Map<string, Set<(ev?: unknown) => void>>()
  return {
    m,
    fire(type: string, ev?: unknown) {
      for (const fn of m.get(type) ?? []) fn(ev)
    },
    add(type: string, fn: (ev?: unknown) => void) {
      if (!m.has(type)) m.set(type, new Set())
      m.get(type)!.add(fn)
    },
  }
}

describe('createAndUploadDraftLesson', () => {
  let listeners: ReturnType<typeof xhrListeners>

  beforeEach(() => {
    listeners = xhrListeners()

    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(null, { status: 200, statusText: 'OK' })),
    )
    createLesson.mockResolvedValue({ lessonId: 'les-1', moduleId: 'm1', order: 0 })
    getUploadUrl
      .mockResolvedValueOnce({ uploadUrl: 'https://s3.example/put-video' })
      .mockResolvedValueOnce({ uploadUrl: 'https://s3.example/put-thumb', thumbnailKey: 'thumb-key-1' })
    markLessonVideoReady.mockResolvedValue({ lessonId: 'les-1', videoStatus: 'ready' })
    captureFrameAtVideoPercent.mockResolvedValue(new Blob([new Uint8Array([0xff, 0xd8])], { type: 'image/jpeg' }))

    class TrackedXHR {
      status = 200
      statusText = 'OK'
      upload = {
        addEventListener: (type: string, fn: EventListener) => {
          if (type === 'progress') {
            queueMicrotask(() =>
              (fn as (e: ProgressEvent) => void)({
                lengthComputable: true,
                loaded: 50,
                total: 100,
              } as ProgressEvent),
            )
          }
        },
      }
      open = vi.fn()
      setRequestHeader = vi.fn()
      send = vi.fn(() => {
        queueMicrotask(() => listeners.fire('load'))
      })
      addEventListener(type: string, fn: EventListener) {
        listeners.add(type, fn as (ev?: unknown) => void)
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.stubGlobal('XMLHttpRequest', TrackedXHR as any)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('creates lesson, PUTs video, uploads thumb, marks ready with thumbnailKey', async () => {
    const progress: number[] = []
    const file = new File([new Uint8Array([1, 2, 3])], 'lesson.mp4', { type: 'video/mp4' })

    await createAndUploadDraftLesson({
      courseId: 'c1',
      lessonInput: { title: 'L1', moduleId: 'm9' },
      videoFile: file,
      onUploadProgress: (n) => progress.push(n),
    })

    expect(createLesson).toHaveBeenCalledWith('c1', { title: 'L1', moduleId: 'm9' })
    expect(getUploadUrl).toHaveBeenNthCalledWith(1, 'lesson.mp4', 'video/mp4', {
      courseId: 'c1',
      lessonId: 'les-1',
    })
    expect(getUploadUrl).toHaveBeenNthCalledWith(2, 'lesson-thumb.jpg', 'image/jpeg', {
      courseId: 'c1',
      lessonId: 'les-1',
      uploadKind: 'lessonThumbnail',
    })
    expect(markLessonVideoReady).toHaveBeenCalledWith('c1', 'les-1', { thumbnailKey: 'thumb-key-1' })
    expect(progress[progress.length - 1]).toBe(100)
    expect(vi.mocked(fetch)).toHaveBeenCalled()
  })

  it('rejects when createLesson fails before upload', async () => {
    createLesson.mockRejectedValueOnce(new Error('quota exceeded'))

    await expect(
      createAndUploadDraftLesson({
        courseId: 'c1',
        lessonInput: { title: 'L1' },
        videoFile: new File([], 'a.mp4', { type: 'video/mp4' }),
        onUploadProgress: vi.fn(),
      }),
    ).rejects.toThrow(/quota exceeded/i)

    expect(getUploadUrl).not.toHaveBeenCalled()
    expect(markLessonVideoReady).not.toHaveBeenCalled()
  })

  it('rejects when video getUploadUrl rejects', async () => {
    getUploadUrl.mockReset()
    getUploadUrl.mockRejectedValueOnce(new Error('presign denied'))

    await expect(
      createAndUploadDraftLesson({
        courseId: 'c1',
        lessonInput: { title: 'L1' },
        videoFile: new File([], 'a.mp4', { type: 'video/mp4' }),
        onUploadProgress: vi.fn(),
      }),
    ).rejects.toThrow(/presign denied/i)

    expect(createLesson).toHaveBeenCalled()
    expect(markLessonVideoReady).not.toHaveBeenCalled()
  })

  it('rejects when video XHR completes with non-2xx', async () => {
    listeners = xhrListeners()
    class FailingXHR {
      status = 500
      statusText = 'Server Error'
      upload = { addEventListener: vi.fn() }
      open = vi.fn()
      setRequestHeader = vi.fn()
      send = vi.fn(() => {
        queueMicrotask(() => listeners.fire('load'))
      })
      addEventListener(type: string, fn: EventListener) {
        listeners.add(type, fn as (ev?: unknown) => void)
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.stubGlobal('XMLHttpRequest', FailingXHR as any)

    await expect(
      createAndUploadDraftLesson({
        courseId: 'c1',
        lessonInput: { title: 'L1' },
        videoFile: new File([], 'a.mp4', { type: 'video/mp4' }),
        onUploadProgress: vi.fn(),
      }),
    ).rejects.toThrow(/Upload failed: Server Error/)

    expect(markLessonVideoReady).not.toHaveBeenCalled()
  })

  it('rejects on video XHR error event', async () => {
    listeners = xhrListeners()
    class NetworkErrorXHR {
      status = 0
      statusText = ''
      upload = { addEventListener: vi.fn() }
      open = vi.fn()
      setRequestHeader = vi.fn()
      send = vi.fn(() => {
        queueMicrotask(() => listeners.fire('error'))
      })
      addEventListener(type: string, fn: EventListener) {
        listeners.add(type, fn as (ev?: unknown) => void)
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.stubGlobal('XMLHttpRequest', NetworkErrorXHR as any)

    await expect(
      createAndUploadDraftLesson({
        courseId: 'c1',
        lessonInput: { title: 'L1' },
        videoFile: new File([], 'a.mp4', { type: 'video/mp4' }),
        onUploadProgress: vi.fn(),
      }),
    ).rejects.toThrow(/^Upload failed$/)

    expect(markLessonVideoReady).not.toHaveBeenCalled()
  })

  it('rejects on video XHR abort event', async () => {
    listeners = xhrListeners()
    class AbortedXHR {
      status = 0
      statusText = ''
      upload = { addEventListener: vi.fn() }
      open = vi.fn()
      setRequestHeader = vi.fn()
      send = vi.fn(() => {
        queueMicrotask(() => listeners.fire('abort'))
      })
      addEventListener(type: string, fn: EventListener) {
        listeners.add(type, fn as (ev?: unknown) => void)
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.stubGlobal('XMLHttpRequest', AbortedXHR as any)

    await expect(
      createAndUploadDraftLesson({
        courseId: 'c1',
        lessonInput: { title: 'L1' },
        videoFile: new File([], 'a.mp4', { type: 'video/mp4' }),
        onUploadProgress: vi.fn(),
      }),
    ).rejects.toThrow(/^Upload aborted$/)

    expect(markLessonVideoReady).not.toHaveBeenCalled()
  })

  it('marks ready without thumbnail when thumbnail PUT fetch is not ok', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 403, statusText: 'Forbidden' }))

    await createAndUploadDraftLesson({
      courseId: 'c1',
      lessonInput: { title: 'L1' },
      videoFile: new File([new Uint8Array([1])], 'lesson.mp4', { type: 'video/mp4' }),
      onUploadProgress: vi.fn(),
    })

    expect(markLessonVideoReady).toHaveBeenCalledWith('c1', 'les-1', undefined)
  })

  it('marks ready without thumbnail when thumbnail getUploadUrl rejects', async () => {
    getUploadUrl.mockReset()
    getUploadUrl
      .mockResolvedValueOnce({ uploadUrl: 'https://s3.example/put-video' })
      .mockRejectedValueOnce(new Error('thumbnail policy'))

    await createAndUploadDraftLesson({
      courseId: 'c1',
      lessonInput: { title: 'L1' },
      videoFile: new File([new Uint8Array([1])], 'lesson.mp4', { type: 'video/mp4' }),
      onUploadProgress: vi.fn(),
    })

    expect(markLessonVideoReady).toHaveBeenCalledWith('c1', 'les-1', undefined)
  })

  it('marks ready without thumbnail when captureFrame throws', async () => {
    captureFrameAtVideoPercent.mockRejectedValueOnce(new Error('decode'))
    getUploadUrl.mockReset()
    getUploadUrl.mockResolvedValueOnce({ uploadUrl: 'https://s3.example/put-video' })

    await createAndUploadDraftLesson({
      courseId: 'c1',
      lessonInput: { title: 'L1' },
      videoFile: new File([], 'a.mp4', { type: 'video/mp4' }),
      onUploadProgress: vi.fn(),
    })

    expect(getUploadUrl).toHaveBeenCalledTimes(1)
    expect(markLessonVideoReady).toHaveBeenCalledWith('c1', 'les-1', undefined)
  })

  it('uses video/mp4 when file type is empty', async () => {
    captureFrameAtVideoPercent.mockRejectedValueOnce(new Error('skip'))
    getUploadUrl.mockReset()
    getUploadUrl.mockResolvedValueOnce({ uploadUrl: 'https://s3.example/put-video' })

    await createAndUploadDraftLesson({
      courseId: 'c1',
      lessonInput: { title: 'L1' },
      videoFile: new File([], 'x.mov', { type: '' }),
      onUploadProgress: vi.fn(),
    })

    expect(getUploadUrl).toHaveBeenCalledWith('x.mov', 'video/mp4', {
      courseId: 'c1',
      lessonId: 'les-1',
    })
  })
})
