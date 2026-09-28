import { httpDelete, httpGet, httpPatch, httpPost } from './client'
import type {
  DeleteLessonNoteResponse,
  LessonNoteItem,
  LessonNoteResponse,
  ListLessonNotesResponse,
} from './types'

export async function listLessonNotes(courseId: string, lessonId: string): Promise<LessonNoteItem[]> {
  const res = await httpGet<ListLessonNotesResponse>(`/courses/${courseId}/lessons/${lessonId}/notes`)
  return res.notes
}

type CreateLessonNoteBody = {
  body: string
  timestampSec?: number
}

export async function createLessonNote(
  courseId: string,
  lessonId: string,
  body: CreateLessonNoteBody,
): Promise<LessonNoteItem> {
  const res = await httpPost<LessonNoteResponse>(`/courses/${courseId}/lessons/${lessonId}/notes`, body)
  return res.note
}

type UpdateLessonNoteBody = {
  body?: string
  timestampSec?: number | null
}

export async function updateLessonNote(
  courseId: string,
  lessonId: string,
  noteId: string,
  body: UpdateLessonNoteBody,
): Promise<LessonNoteItem> {
  const res = await httpPatch<LessonNoteResponse>(
    `/courses/${courseId}/lessons/${lessonId}/notes/${noteId}`,
    body,
  )
  return res.note
}

export async function deleteLessonNote(
  courseId: string,
  lessonId: string,
  noteId: string,
): Promise<DeleteLessonNoteResponse> {
  return httpDelete<DeleteLessonNoteResponse>(
    `/courses/${courseId}/lessons/${lessonId}/notes/${noteId}`,
  )
}
