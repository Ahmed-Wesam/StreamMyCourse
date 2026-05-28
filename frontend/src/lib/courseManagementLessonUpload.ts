import {
  createLesson,
  getUploadUrl,
  markLessonVideoReady,
} from './api/catalog'
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

/**
 * Create a draft lesson, upload video via the active provider, best-effort lesson thumbnail,
 * then mark video ready when the provider expects immediate readiness (S3).
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

  const marksReadyOnUpload = videoUpload.provider === 's3'

  if (marksReadyOnUpload) {
    onUploadProgress(95)
    await markLessonVideoReady(
      courseId,
      lessonResult.lessonId,
      lessonThumbKey ? { thumbnailKey: lessonThumbKey } : undefined,
    )
  }

  onUploadProgress(100)
  return {
    lessonId: lessonResult.lessonId,
    videoStatus: marksReadyOnUpload ? 'ready' : 'pending',
  }
}
