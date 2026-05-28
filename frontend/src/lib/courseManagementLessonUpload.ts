import {
  createLesson,
  getUploadUrl,
  markLessonVideoReady,
} from './api/catalog'
import { ApiError } from './api/client'
import { captureFrameAtVideoPercent } from './videoThumbnail'

type DraftLessonUploadInput = {
  title: string
  moduleId?: string
}

type CreateAndUploadDraftLessonParams = {
  courseId: string
  lessonInput: DraftLessonUploadInput
  videoFile: File
  onUploadProgress: (percent: number) => void
}

type DraftLessonUploadResult = {
  lessonId: string
  videoStatus: 'ready' | 'pending'
}

type VideoUploadInit = {
  uploadUrl: string
  provider: 'kinescope' | 's3'
  uploadMethod?: 'post' | 'tus'
}

function uploadWithProgress(
  xhr: XMLHttpRequest,
  body: Blob,
  onUploadProgress: (percent: number) => void,
  progressBase: number,
  progressSpan: number,
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const ratio = event.loaded / event.total
        onUploadProgress(Math.round(ratio * progressSpan) + progressBase)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText || String(xhr.status)}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Upload failed')))
    xhr.addEventListener('abort', () => reject(new Error('Upload aborted')))

    xhr.send(body)
  })
}

async function uploadLessonVideoFile(
  videoUpload: VideoUploadInit,
  videoFile: File,
  contentType: string,
  onUploadProgress: (percent: number) => void,
): Promise<void> {
  if (videoUpload.provider === 'kinescope') {
    if (videoUpload.uploadMethod === 'tus') {
      throw new Error('Videos over 5 GB require resumable upload. Use a smaller file.')
    }
    const xhr = new XMLHttpRequest()
    xhr.open('POST', videoUpload.uploadUrl, true)
    await uploadWithProgress(xhr, videoFile, onUploadProgress, 40, 50)
    return
  }

  const xhr = new XMLHttpRequest()
  xhr.open('PUT', videoUpload.uploadUrl, true)
  xhr.setRequestHeader('Content-Type', contentType)
  await uploadWithProgress(xhr, videoFile, onUploadProgress, 40, 50)
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Mark lesson ready after upload; Kinescope may still be transcoding so retry until ready or timeout. */
async function markLessonVideoReadyAfterUpload(
  courseId: string,
  lessonId: string,
  provider: VideoUploadInit['provider'],
  thumbnailKey?: string,
): Promise<'ready' | 'pending'> {
  const options = thumbnailKey ? { thumbnailKey } : undefined
  const maxAttempts = provider === 'kinescope' ? 30 : 1
  const retryDelayMs = 10_000

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const result = await markLessonVideoReady(courseId, lessonId, options)
      if (result.videoStatus === 'ready') return 'ready'
    } catch (err) {
      const stillProcessing =
        provider === 'kinescope' &&
        err instanceof ApiError &&
        err.status === 400 &&
        (err.code === 'video_not_ready' || /processing/i.test(err.message))
      if (stillProcessing && attempt < maxAttempts) {
        await sleep(retryDelayMs)
        continue
      }
      if (stillProcessing) return 'pending'
      throw err
    }
  }
  return 'pending'
}

/**
 * Create a draft lesson, upload video via the active provider, best-effort lesson thumbnail,
 * then mark video ready (immediate for S3; polled for Kinescope while transcoding).
 */
export async function createAndUploadDraftLesson({
  courseId,
  lessonInput,
  videoFile,
  onUploadProgress,
}: CreateAndUploadDraftLessonParams): Promise<DraftLessonUploadResult> {
  onUploadProgress(20)
  const lessonResult = await createLesson(courseId, lessonInput)

  onUploadProgress(30)
  const contentType = videoFile.type || 'video/mp4'
  const videoUpload = await getUploadUrl(videoFile.name, contentType, {
    courseId,
    lessonId: lessonResult.lessonId,
    ...(videoFile.size > 0 ? { filesize: videoFile.size } : {}),
  })

  onUploadProgress(40)
  await uploadLessonVideoFile(videoUpload, videoFile, contentType, onUploadProgress)

  onUploadProgress(92)
  let lessonThumbKey: string | undefined
  try {
    const jpeg = await captureFrameAtVideoPercent(videoFile, 0.2)
    const thumb = await getUploadUrl('lesson-thumb.jpg', 'image/jpeg', {
      courseId,
      lessonId: lessonResult.lessonId,
      uploadKind: 'lessonThumbnail',
    })
    if (thumb.thumbnailKey) {
      const putThumb = await fetch(thumb.uploadUrl, {
        method: 'PUT',
        body: jpeg,
        headers: { 'Content-Type': 'image/jpeg' },
      })
      if (putThumb.ok) {
        lessonThumbKey = thumb.thumbnailKey
      }
    }
  } catch {
    // Continue without lesson thumbnail if decode/seek fails
  }

  onUploadProgress(95)
  const videoStatus = await markLessonVideoReadyAfterUpload(
    courseId,
    lessonResult.lessonId,
    videoUpload.provider,
    lessonThumbKey,
  )

  onUploadProgress(100)
  return {
    lessonId: lessonResult.lessonId,
    videoStatus,
  }
}
