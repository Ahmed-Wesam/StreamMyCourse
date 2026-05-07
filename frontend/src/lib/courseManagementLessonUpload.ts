import {
  createLesson,
  getUploadUrl,
  markLessonVideoReady,
} from './api'
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

/**
 * Create a draft lesson, PUT the video to S3, best-effort lesson thumbnail, then mark video ready.
 * Used by the instructor course editor; keeps XHR + S3 details out of the page component.
 */
export async function createAndUploadDraftLesson({
  courseId,
  lessonInput,
  videoFile,
  onUploadProgress,
}: CreateAndUploadDraftLessonParams): Promise<void> {
  onUploadProgress(20)
  const lessonResult = await createLesson(courseId, lessonInput)

  onUploadProgress(30)
  const contentType = videoFile.type || 'video/mp4'
  const { uploadUrl } = await getUploadUrl(videoFile.name, contentType, {
    courseId,
    lessonId: lessonResult.lessonId,
  })

  onUploadProgress(40)
  const xhr = new XMLHttpRequest()

  await new Promise<void>((resolve, reject) => {
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 50) + 40
        onUploadProgress(percent)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Upload failed')))
    xhr.addEventListener('abort', () => reject(new Error('Upload aborted')))

    xhr.open('PUT', uploadUrl, true)
    xhr.setRequestHeader('Content-Type', contentType)
    xhr.send(videoFile)
  })

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
  await markLessonVideoReady(
    courseId,
    lessonResult.lessonId,
    lessonThumbKey ? { thumbnailKey: lessonThumbKey } : undefined,
  )

  onUploadProgress(100)
}
