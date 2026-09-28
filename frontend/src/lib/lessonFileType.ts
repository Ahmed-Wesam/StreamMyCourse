/** Maps allowed lesson attachment extensions to catalog `fileType` values (RS-11). */

import type { LessonFileStatus } from './api/types'

const EXT_TO_FILE_TYPE: Record<string, string> = {
  pdf: 'pdf',
  csv: 'csv',
  xlsx: 'xlsx',
  docx: 'docx',
  sav: 'sav',
}

const FILE_TYPE_TO_CONTENT_TYPE: Record<string, string> = {
  pdf: 'application/pdf',
  csv: 'text/csv',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  sav: 'application/x-spss-sav',
}

export function fileTypeFromFileName(filename: string): string {
  const base = (filename || '').trim().toLowerCase()
  const dot = base.lastIndexOf('.')
  const ext = dot >= 0 ? base.slice(dot + 1) : ''
  const fileType = EXT_TO_FILE_TYPE[ext]
  if (!fileType) {
    throw new Error('Unsupported file type. Use PDF, CSV, XLSX, DOCX, or SAV.')
  }
  return fileType
}

export function contentTypeForLessonFileType(fileType: string): string {
  const ct = FILE_TYPE_TO_CONTENT_TYPE[fileType]
  if (!ct) {
    throw new Error('Unsupported file type.')
  }
  return ct
}

export const LESSON_ATTACHMENT_ACCEPT = '.pdf,.csv,.xlsx,.docx,.sav'

export function isReadyLessonFile(status: LessonFileStatus): boolean {
  return status === 'ready'
}
