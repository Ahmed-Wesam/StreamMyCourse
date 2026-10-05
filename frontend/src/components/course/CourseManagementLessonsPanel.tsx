import { useEffect, useState } from 'react'

import type { Course, Lesson, LessonFileKind, LessonFileListItem } from '../../lib/api/types'
import { LESSON_ATTACHMENT_ACCEPT } from '../../lib/lessonFileType'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'

type Props = {
  course: Course
  sortedLessons: Lesson[]
  moduleTitleById: Map<string, string>
  lessonFilesByLessonId: Record<string, LessonFileListItem[]>
  attachingLessonId: string | null
  onAddLessonClick: () => void
  onDeleteLesson: (lessonId: string) => void
  onAttachLessonFile: (params: {
    lessonId: string
    title: string
    kind: LessonFileKind
    file: File
  }) => Promise<void>
  onDeleteLessonFile: (lessonId: string, fileId: string) => Promise<void>
  onSaveTranscript?: (lessonId: string, transcript: string) => Promise<void>
}

export function CourseManagementLessonsPanel({
  course,
  sortedLessons,
  moduleTitleById,
  lessonFilesByLessonId,
  attachingLessonId,
  onAddLessonClick,
  onDeleteLesson,
  onAttachLessonFile,
  onDeleteLessonFile,
  onSaveTranscript,
}: Props) {
  const [draftTitleByLesson, setDraftTitleByLesson] = useState<Record<string, string>>({})
  const [draftKindByLesson, setDraftKindByLesson] = useState<Record<string, 'resource' | 'download'>>({})
  const [draftFileByLesson, setDraftFileByLesson] = useState<Record<string, File | null>>({})
  const [transcriptByLesson, setTranscriptByLesson] = useState<Record<string, string>>({})
  const [savingTranscriptId, setSavingTranscriptId] = useState<string | null>(null)

  useEffect(() => {
    setTranscriptByLesson((prev) => {
      const next = { ...prev }
      let changed = false
      for (const lesson of sortedLessons) {
        if (next[lesson.id] === undefined) {
          next[lesson.id] = lesson.transcript ?? ''
          changed = true
        }
      }
      return changed ? next : prev
    })
  }, [sortedLessons])

  const canManageAttachments = course.status === 'DRAFT'

  return (
    <Card className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-extrabold text-rs-navy">Lessons ({sortedLessons.length})</h2>
        {course.status === 'DRAFT' && (
          <Button type="button" size="sm" onClick={onAddLessonClick}>
            + Add Lesson
          </Button>
        )}
      </div>

      {sortedLessons.length === 0 ? (
        <div className="rounded-lg bg-rs-sky-2 py-12 text-center">
          <p className="text-rs-body">No lessons yet</p>
          {course.status === 'DRAFT' && (
            <p className="mt-1 text-sm text-rs-muted">Add your first lesson with a video</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {sortedLessons.map((lesson, index) => {
            const files = lessonFilesByLessonId[lesson.id] ?? []
            const draftTitle = draftTitleByLesson[lesson.id] ?? ''
            const draftKind = draftKindByLesson[lesson.id] ?? 'resource'
            const draftFile = draftFileByLesson[lesson.id] ?? null
            const attaching = attachingLessonId === lesson.id

            return (
              <div
                key={lesson.id}
                className="rounded-lg border border-rs-line p-4 transition-colors hover:bg-rs-sky-2/40"
                data-testid={`lesson-row-${lesson.id}`}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <span className="font-semibold text-rs-muted">{index + 1}</span>
                    <div>
                      <h3 className="font-semibold text-rs-navy">{lesson.title}</h3>
                      {moduleTitleById.get(lesson.moduleId) && (
                        <div className="mt-1 text-xs text-rs-muted">{moduleTitleById.get(lesson.moduleId)}</div>
                      )}
                      <div className="mt-1 flex items-center gap-2">
                        <Badge tone={lesson.videoStatus === 'ready' ? 'success' : 'blue'}>
                          {lesson.videoStatus === 'ready' ? '✓ Ready' : '⏳ Pending'}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  {course.status === 'DRAFT' && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label="Delete Lesson"
                      className="!text-red-700 hover:!bg-red-50"
                      onClick={() => void onDeleteLesson(lesson.id)}
                    >
                      Delete
                    </Button>
                  )}
                </div>

                <form
                  className="mt-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    if (!onSaveTranscript) return
                    const transcript = transcriptByLesson[lesson.id] ?? lesson.transcript ?? ''
                    setSavingTranscriptId(lesson.id)
                    void onSaveTranscript(lesson.id, transcript).finally(() => {
                      setSavingTranscriptId((current) => (current === lesson.id ? null : current))
                    })
                  }}
                >
                  <Field label="Lecture transcript">
                    <textarea
                      rows={5}
                      value={transcriptByLesson[lesson.id] ?? lesson.transcript ?? ''}
                      onChange={(event) =>
                        setTranscriptByLesson((prev) => ({
                          ...prev,
                          [lesson.id]: event.target.value,
                        }))
                      }
                    />
                  </Field>
                  <Button type="submit" size="sm" disabled={savingTranscriptId === lesson.id}>
                    {savingTranscriptId === lesson.id ? 'Saving…' : 'Save transcript'}
                  </Button>
                </form>

                <div className="mt-4 border-t border-rs-line pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-rs-muted">Lesson files</p>
                  {files.length === 0 ? (
                    <p className="mt-2 text-sm text-rs-muted">No attachments yet.</p>
                  ) : (
                    <ul className="mt-2 space-y-2" data-testid={`lesson-file-list-${lesson.id}`}>
                      {files.map((file) => (
                        <li
                          key={file.fileId}
                          className="flex items-center justify-between gap-3 rounded-md border border-rs-line bg-white px-3 py-2 text-sm"
                        >
                          <div>
                            <span className="font-medium text-rs-navy">{file.title}</span>
                            <span className="ml-2 text-xs uppercase text-rs-muted">
                              {file.kind} · {file.fileType}
                            </span>
                            {file.status === 'pending' ? (
                              <span className="ml-2 text-xs text-rs-muted">(pending)</span>
                            ) : null}
                          </div>
                          {canManageAttachments ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="!text-red-700"
                              aria-label={`Delete file ${file.title}`}
                              onClick={() => void onDeleteLessonFile(lesson.id, file.fileId)}
                            >
                              Remove
                            </Button>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}

                  {canManageAttachments ? (
                    <form
                      className="mt-4 space-y-3 rounded-lg bg-rs-sky-2/50 p-3"
                      data-testid={`lesson-attach-form-${lesson.id}`}
                      onSubmit={(e) => {
                        e.preventDefault()
                        if (!draftTitle.trim() || !draftFile) return
                        void onAttachLessonFile({
                          lessonId: lesson.id,
                          title: draftTitle,
                          kind: draftKind,
                          file: draftFile,
                        }).then(() => {
                          setDraftTitleByLesson((prev) => ({ ...prev, [lesson.id]: '' }))
                          setDraftFileByLesson((prev) => ({ ...prev, [lesson.id]: null }))
                        })
                      }}
                    >
                      <Field
                        label="Title"
                        value={draftTitle}
                        onChange={(e) =>
                          setDraftTitleByLesson((prev) => ({ ...prev, [lesson.id]: e.target.value }))
                        }
                      />
                      <Field label="Kind" className="mb-0">
                        <select
                          className="min-h-11 w-full rounded-xl border border-rs-line bg-white px-3 text-sm"
                          value={draftKind}
                          onChange={(e) =>
                            setDraftKindByLesson((prev) => ({
                              ...prev,
                              [lesson.id]: e.target.value as 'resource' | 'download',
                            }))
                          }
                          aria-label="File kind"
                        >
                          <option value="resource">Resource</option>
                          <option value="download">Download</option>
                        </select>
                      </Field>
                      <Field label="File" className="mb-0">
                        <input
                          type="file"
                          accept={LESSON_ATTACHMENT_ACCEPT}
                          onChange={(e) =>
                            setDraftFileByLesson((prev) => ({
                              ...prev,
                              [lesson.id]: e.target.files?.[0] ?? null,
                            }))
                          }
                          aria-label="Attachment file"
                        />
                      </Field>
                      <Button
                        type="submit"
                        size="sm"
                        disabled={attaching || !draftTitle.trim() || !draftFile}
                      >
                        {attaching ? 'Uploading…' : 'Attach file'}
                      </Button>
                    </form>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
