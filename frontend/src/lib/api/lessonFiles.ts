import { failedResponseError, httpDelete, httpGet, httpPost, httpPut } from './client'
import type {
  CompleteLessonFileResponse,
  CreateLessonFileResponse,
  DeleteLessonFileResponse,
  LessonFileDownloadUrlResponse,
  LessonFileKind,
  LessonFileListItem,
} from './types'

export async function listLessonFiles(courseId: string, lessonId: string): Promise<LessonFileListItem[]> {
  return httpGet<LessonFileListItem[]>(`/courses/${courseId}/lessons/${lessonId}/files`)
}

type CreateLessonFileBody = {
  title: string
  kind: LessonFileKind
  fileType: string
  byteSize: number
}

export async function createLessonFile(
  courseId: string,
  lessonId: string,
  body: CreateLessonFileBody,
): Promise<CreateLessonFileResponse> {
  return httpPost<CreateLessonFileResponse>(`/courses/${courseId}/lessons/${lessonId}/files`, body)
}

export async function completeLessonFile(
  courseId: string,
  lessonId: string,
  fileId: string,
): Promise<CompleteLessonFileResponse> {
  return httpPut<CompleteLessonFileResponse>(
    `/courses/${courseId}/lessons/${lessonId}/files/${fileId}/complete`,
    {},
  )
}

export async function getLessonFileDownloadUrl(
  courseId: string,
  lessonId: string,
  fileId: string,
): Promise<LessonFileDownloadUrlResponse> {
  return httpGet<LessonFileDownloadUrlResponse>(
    `/courses/${courseId}/lessons/${lessonId}/files/${fileId}/url`,
  )
}

export async function deleteLessonFile(
  courseId: string,
  lessonId: string,
  fileId: string,
): Promise<DeleteLessonFileResponse> {
  return httpDelete<DeleteLessonFileResponse>(`/courses/${courseId}/lessons/${lessonId}/files/${fileId}`)
}

/** PUT bytes to the presigned URL returned from `createLessonFile`. */
export async function putLessonFileToUploadUrl(
  uploadUrl: string,
  file: Blob,
  contentType: string,
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,
  })
  if (!res.ok) {
    throw await failedResponseError(res)
  }
}
