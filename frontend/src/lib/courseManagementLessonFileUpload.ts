import {
  completeLessonFile,
  createLessonFile,
  putLessonFileToUploadUrl,
} from './api/lessonFiles'
import { contentTypeForLessonFileType, fileTypeFromFileName } from './lessonFileType'

export async function createAndUploadLessonAttachment(params: {
  courseId: string
  lessonId: string
  title: string
  kind: 'resource' | 'download'
  file: File
}): Promise<{ fileId: string }> {
  const fileType = fileTypeFromFileName(params.file.name)
  const contentType = contentTypeForLessonFileType(fileType)
  const created = await createLessonFile(params.courseId, params.lessonId, {
    title: params.title.trim(),
    kind: params.kind,
    fileType,
    byteSize: params.file.size,
  })
  await putLessonFileToUploadUrl(created.uploadUrl, params.file, contentType)
  await completeLessonFile(params.courseId, params.lessonId, created.fileId)
  return { fileId: created.fileId }
}
