import { useCallback, useEffect, useId, useState } from 'react'

import { listLessonFiles } from '../../lib/api/lessonFiles'
import {
  createLessonNote,
  deleteLessonNote,
  listLessonNotes,
  updateLessonNote,
} from '../../lib/api/lessonNotes'
import type { LessonFileListItem, LessonNoteItem } from '../../lib/api/types'
import { isReadyLessonFile } from '../../lib/lessonFileType'
import { formatNoteTimestamp, openLessonFileItem } from './lessonPlayerFileActions'

const LESSON_PLAYER_TAB_IDS = [
  'overview',
  'resources',
  'downloads',
  'notes',
  'assignments',
] as const

type LessonPlayerTabId = (typeof LESSON_PLAYER_TAB_IDS)[number]

const TAB_LABELS: Record<LessonPlayerTabId, string> = {
  overview: 'Overview',
  resources: 'Resources',
  downloads: 'Downloads',
  notes: 'Notes',
  assignments: 'Assignments',
}

const ASSIGNMENTS_PLACEHOLDER = 'Not available yet.'

const EMPTY_RESOURCES = 'No resources for this lesson yet.'
const EMPTY_DOWNLOADS = 'No downloads for this lesson yet.'
const EMPTY_NOTES = 'You have not added any notes for this lesson yet.'

function LessonFileCards({
  files,
  emptyMessage,
  onOpenFile,
  openingFileId,
}: {
  files: LessonFileListItem[]
  emptyMessage: string
  onOpenFile: (file: LessonFileListItem) => void
  openingFileId: string | null
}) {
  if (files.length === 0) {
    return (
      <p className="text-sm text-rs-muted" data-testid="lesson-player-files-empty">
        {emptyMessage}
      </p>
    )
  }

  return (
    <ul className="space-y-2" data-testid="lesson-player-file-list">
      {files.map((file) => (
        <li key={file.fileId}>
          <button
            type="button"
            disabled={!isReadyLessonFile(file.status) || openingFileId === file.fileId}
            onClick={() => onOpenFile(file)}
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-rs-line bg-rs-sky-2/30 px-4 py-3 text-left text-sm transition-colors hover:bg-rs-sky-2/60 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="font-semibold text-rs-navy">{file.title}</span>
            <span className="shrink-0 text-xs uppercase tracking-wide text-rs-muted">
              {isReadyLessonFile(file.status) ? file.fileType : 'Processing…'}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function LessonNotesPanel({
  notes,
  playbackPositionSec,
  onCreate,
  onUpdate,
  onDelete,
  busy,
}: {
  notes: LessonNoteItem[]
  playbackPositionSec: number
  onCreate: (body: string, timestampSec?: number) => Promise<void>
  onUpdate: (noteId: string, body: string) => Promise<void>
  onDelete: (noteId: string) => Promise<void>
  busy: boolean
}) {
  const [draft, setDraft] = useState('')
  const [linkTimestamp, setLinkTimestamp] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState('')

  const canLinkTimestamp = playbackPositionSec > 0

  const startEdit = (note: LessonNoteItem) => {
    setEditingId(note.id)
    setEditDraft(note.body)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditDraft('')
  }

  return (
    <div className="space-y-4">
      {notes.length === 0 ? (
        <p className="text-sm text-rs-muted" data-testid="lesson-player-notes-empty">
          {EMPTY_NOTES}
        </p>
      ) : (
        <ul className="space-y-3" data-testid="lesson-player-note-list">
          {notes.map((note) => (
            <li key={note.id} className="rounded-lg border border-rs-line px-4 py-3">
              {editingId === note.id ? (
                <div className="space-y-2">
                  <textarea
                    className="min-h-[88px] w-full rounded-lg border border-rs-line px-3 py-2 text-sm"
                    value={editDraft}
                    onChange={(e) => setEditDraft(e.target.value)}
                    aria-label="Edit note"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy || !editDraft.trim()}
                      className="rounded-lg bg-rs-navy px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                      onClick={() => void onUpdate(note.id, editDraft).then(cancelEdit)}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      className="rounded-lg border border-rs-line px-3 py-1.5 text-xs font-semibold text-rs-navy"
                      onClick={cancelEdit}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {note.timestampSec != null ? (
                    <div className="mb-1 text-xs font-semibold text-rs-blue">
                      At {formatNoteTimestamp(note.timestampSec)}
                    </div>
                  ) : null}
                  <p className="whitespace-pre-wrap text-sm text-rs-body">{note.body}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="text-xs font-semibold text-rs-blue hover:underline"
                      onClick={() => startEdit(note)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="text-xs font-semibold text-red-700 hover:underline"
                      onClick={() => void onDelete(note.id)}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="border-t border-rs-line pt-4">
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-rs-muted">
          Add a note
        </label>
        <textarea
          className="min-h-[96px] w-full rounded-lg border border-rs-line px-3 py-2 text-sm"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          aria-label="New note"
        />
        {canLinkTimestamp ? (
          <label className="mt-2 flex items-center gap-2 text-sm text-rs-body">
            <input
              type="checkbox"
              checked={linkTimestamp}
              onChange={(e) => setLinkTimestamp(e.target.checked)}
            />
            Link to current playback time ({formatNoteTimestamp(playbackPositionSec)})
          </label>
        ) : null}
        <button
          type="button"
          disabled={busy || !draft.trim()}
          className="mt-3 rounded-lg bg-rs-grad-cta px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() =>
            void onCreate(
              draft,
              linkTimestamp && canLinkTimestamp ? playbackPositionSec : undefined,
            ).then(() => {
              setDraft('')
              setLinkTimestamp(false)
            })
          }
        >
          Save note
        </button>
      </div>
    </div>
  )
}

export function LessonPlayerTabs({
  courseId,
  lessonId,
  courseDescription,
  activeModuleLabel,
  activeLessonTitle,
  playbackPositionSec = 0,
  contentEnabled = true,
}: {
  courseId?: string
  lessonId?: string
  courseDescription?: string
  activeModuleLabel: string
  activeLessonTitle: string
  playbackPositionSec?: number
  /** When false, skip lesson file/note API calls (paywall / sign-in). */
  contentEnabled?: boolean
}) {
  const [activeTab, setActiveTab] = useState<LessonPlayerTabId>('overview')
  const baseId = useId()
  const [files, setFiles] = useState<LessonFileListItem[]>([])
  const [notes, setNotes] = useState<LessonNoteItem[]>([])
  const [openingFileId, setOpeningFileId] = useState<string | null>(null)
  const [notesBusy, setNotesBusy] = useState(false)

  const lessonContext = [activeModuleLabel, activeLessonTitle].filter(Boolean).join(' · ')
  const trimmedDescription = courseDescription?.trim() ?? ''

  const loadAttachments = useCallback(async () => {
    if (!contentEnabled || !courseId || !lessonId) {
      setFiles([])
      setNotes([])
      return
    }
    try {
      const [fileRows, noteRows] = await Promise.all([
        listLessonFiles(courseId, lessonId),
        listLessonNotes(courseId, lessonId),
      ])
      setFiles(fileRows)
      setNotes(noteRows)
    } catch {
      setFiles([])
      setNotes([])
    }
  }, [contentEnabled, courseId, lessonId])

  useEffect(() => {
    void loadAttachments()
  }, [loadAttachments])

  const resourceFiles = files.filter((f) => f.kind === 'resource' && isReadyLessonFile(f.status))
  const downloadFiles = files.filter((f) => f.kind === 'download' && isReadyLessonFile(f.status))

  const handleOpenFile = async (file: LessonFileListItem) => {
    if (!courseId || !lessonId || !isReadyLessonFile(file.status)) return
    setOpeningFileId(file.fileId)
    try {
      await openLessonFileItem(courseId, lessonId, file)
    } finally {
      setOpeningFileId(null)
    }
  }

  const handleCreateNote = async (body: string, timestampSec?: number) => {
    if (!courseId || !lessonId) return
    setNotesBusy(true)
    try {
      const note = await createLessonNote(courseId, lessonId, {
        body: body.trim(),
        ...(timestampSec != null ? { timestampSec } : {}),
      })
      setNotes((prev) => [...prev, note])
    } finally {
      setNotesBusy(false)
    }
  }

  const handleUpdateNote = async (noteId: string, body: string) => {
    if (!courseId || !lessonId) return
    setNotesBusy(true)
    try {
      const note = await updateLessonNote(courseId, lessonId, noteId, { body: body.trim() })
      setNotes((prev) => prev.map((n) => (n.id === noteId ? note : n)))
    } finally {
      setNotesBusy(false)
    }
  }

  const handleDeleteNote = async (noteId: string) => {
    if (!courseId || !lessonId) return
    setNotesBusy(true)
    try {
      await deleteLessonNote(courseId, lessonId, noteId)
      setNotes((prev) => prev.filter((n) => n.id !== noteId))
    } finally {
      setNotesBusy(false)
    }
  }

  return (
    <div className="mt-5">
      <div
        role="tablist"
        aria-label="Lesson content"
        className="flex gap-1 overflow-x-auto border-b border-rs-line pb-px [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {LESSON_PLAYER_TAB_IDS.map((tabId) => {
          const selected = activeTab === tabId
          return (
            <button
              key={tabId}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tabId}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${tabId}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveTab(tabId)}
              className={`shrink-0 rounded-t-lg px-3 py-2.5 text-sm font-semibold transition-colors ${
                selected
                  ? 'border border-b-0 border-rs-line bg-white text-rs-navy'
                  : 'text-rs-muted hover:bg-rs-sky-2/80 hover:text-rs-navy'
              }`}
            >
              {TAB_LABELS[tabId]}
            </button>
          )
        })}
      </div>

      {LESSON_PLAYER_TAB_IDS.map((tabId) => {
        const selected = activeTab === tabId
        return (
          <div
            key={tabId}
            role="tabpanel"
            id={`${baseId}-panel-${tabId}`}
            aria-labelledby={`${baseId}-tab-${tabId}`}
            hidden={!selected}
            className="rounded-b-rs-sm border border-t-0 border-rs-line bg-white px-4 py-5 shadow-rs-sm"
            data-testid={selected ? 'lesson-player-tab-panel' : undefined}
          >
            {tabId === 'overview' ? (
              <div className="space-y-3 text-sm leading-relaxed text-rs-body">
                {trimmedDescription ? <p>{trimmedDescription}</p> : null}
                {lessonContext ? (
                  <p className={trimmedDescription ? 'text-rs-muted' : undefined}>{lessonContext}</p>
                ) : null}
              </div>
            ) : tabId === 'resources' ? (
              <LessonFileCards
                files={resourceFiles}
                emptyMessage={EMPTY_RESOURCES}
                onOpenFile={(file) => void handleOpenFile(file)}
                openingFileId={openingFileId}
              />
            ) : tabId === 'downloads' ? (
              <LessonFileCards
                files={downloadFiles}
                emptyMessage={EMPTY_DOWNLOADS}
                onOpenFile={(file) => void handleOpenFile(file)}
                openingFileId={openingFileId}
              />
            ) : tabId === 'notes' ? (
              contentEnabled && courseId && lessonId ? (
                <LessonNotesPanel
                  notes={notes}
                  playbackPositionSec={playbackPositionSec}
                  onCreate={handleCreateNote}
                  onUpdate={handleUpdateNote}
                  onDelete={handleDeleteNote}
                  busy={notesBusy}
                />
              ) : (
                <p className="text-sm text-rs-muted" data-testid="lesson-player-notes-empty">
                  {EMPTY_NOTES}
                </p>
              )
            ) : (
              <p
                className="text-sm text-rs-muted"
                data-testid={selected ? 'lesson-player-tab-placeholder' : undefined}
              >
                {ASSIGNMENTS_PLACEHOLDER}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
