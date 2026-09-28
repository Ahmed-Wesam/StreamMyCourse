import { getLessonFileDownloadUrl } from '../../lib/api/lessonFiles'
import type { LessonFileListItem } from '../../lib/api/types'

export async function openLessonFileItem(
  courseId: string,
  lessonId: string,
  file: LessonFileListItem,
  getUrl: typeof getLessonFileDownloadUrl = getLessonFileDownloadUrl,
): Promise<void> {
  const { url } = await getUrl(courseId, lessonId, file.fileId)
  if (file.kind === 'resource' && file.fileType === 'pdf') {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.rel = 'noopener'
  anchor.target = '_blank'
  anchor.download = ''
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

export function formatNoteTimestamp(sec: number): string {
  const total = Math.max(0, Math.floor(sec))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
