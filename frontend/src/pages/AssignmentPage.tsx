import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { SafeRichText } from '../components/assignments/SafeRichText'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'
import {
  completeAssignmentSubmissionFile,
  createAssignmentSubmission,
  createAssignmentSubmissionFile,
  getAssignment,
  getAssignmentImageUrl,
  putAssignmentUpload,
  submitAssignmentSubmission,
} from '../lib/api/assignments'
import type { Assignment, AssignmentNarrative } from '../lib/api/types'
import { contentTypeForLessonFileType, fileTypeFromFileName, LESSON_ATTACHMENT_ACCEPT } from '../lib/lessonFileType'
import { usePageTitle } from '../lib/page-title'

const SUBMISSION_MAX_BYTES = 100 * 1024 * 1024
const SUBMISSION_ACCEPT_HINT = `${LESSON_ATTACHMENT_ACCEPT} (max 100 MiB)`

function NarrativeBlock({
  courseId,
  assignmentId,
  slot,
  narrative,
  heading,
}: {
  courseId: string
  assignmentId: string
  slot: 'instructions' | 'rubric'
  narrative: AssignmentNarrative
  heading: string
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  useEffect(() => {
    if (narrative.mode !== 'image' || !narrative.imageReady) {
      setImageUrl(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const { url } = await getAssignmentImageUrl(courseId, assignmentId, slot)
        if (!cancelled) setImageUrl(url)
      } catch {
        if (!cancelled) setImageUrl(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [courseId, assignmentId, slot, narrative.mode, narrative.imageReady])

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-bold uppercase tracking-wide text-rs-muted">{heading}</h2>
      {narrative.mode === 'plain' ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-rs-body">{narrative.text ?? ''}</p>
      ) : null}
      {narrative.mode === 'rich' && narrative.html ? (
        <SafeRichText className="prose prose-sm max-w-none text-rs-body" html={narrative.html} />
      ) : null}
      {narrative.mode === 'image' ? (
        imageUrl ? (
          <img src={imageUrl} alt={heading} className="max-h-96 max-w-full rounded-lg border border-rs-line" />
        ) : (
          <p className="text-sm text-rs-muted">Image unavailable.</p>
        )
      ) : null}
    </section>
  )
}

export default function AssignmentPage() {
  usePageTitle('Assignment')
  const { courseId: courseIdParam, assignmentId: assignmentIdParam } = useParams<{
    courseId: string
    assignmentId: string
  }>()
  const courseId = courseIdParam?.trim() ?? ''
  const assignmentId = assignmentIdParam?.trim() ?? ''

  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!courseId || !assignmentId) {
      setAssignment(null)
      setError('Missing course or assignment id.')
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const row = await getAssignment(courseId, assignmentId)
        if (!cancelled) setAssignment(row)
      } catch {
        if (!cancelled) {
          setAssignment(null)
          setError('Could not load this assignment.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [courseId, assignmentId])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!assignment || assignment.locked || busy) return
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setError('Choose a file to upload.')
      return
    }
    if (file.size <= 0 || file.size > SUBMISSION_MAX_BYTES) {
      setError('File must be between 1 byte and 100 MiB.')
      return
    }

    let fileType: string
    try {
      fileType = fileTypeFromFileName(file.name)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unsupported file type.')
      return
    }

    setBusy(true)
    setError(null)
    setStatusMessage(null)
    try {
      const draft = await createAssignmentSubmission(courseId, assignmentId)
      const contentType = contentTypeForLessonFileType(fileType)
      const { fileId, uploadUrl } = await createAssignmentSubmissionFile(
        courseId,
        assignmentId,
        draft.id,
        { title: file.name, fileType, byteSize: file.size },
      )
      await putAssignmentUpload(uploadUrl, file, contentType)
      await completeAssignmentSubmissionFile(courseId, assignmentId, draft.id, fileId)
      const noteTrimmed = note.trim()
      await submitAssignmentSubmission(
        courseId,
        assignmentId,
        draft.id,
        noteTrimmed ? { note: noteTrimmed } : {},
      )
      const refreshed = await getAssignment(courseId, assignmentId)
      if (mountedRef.current) {
        setAssignment(refreshed)
        setNote('')
        if (fileInputRef.current) fileInputRef.current.value = ''
        setStatusMessage('Submission sent.')
      }
    } catch {
      if (mountedRef.current) setError('Could not submit this assignment.')
    } finally {
      if (mountedRef.current) setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-10 text-sm text-rs-muted" data-testid="assignment-page">
        Loading assignment…
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-10" data-testid="assignment-page">
        <p className="text-sm text-red-700">{error ?? 'Assignment not found.'}</p>
        <Button to={courseId ? `/courses/${courseId}` : '/courses'} variant="ghost" className="mt-4">
          Back to course
        </Button>
      </div>
    )
  }

  const latest = assignment.myLatest

  return (
    <div className="min-h-screen bg-gradient-to-b from-rs-sky-2 to-white text-rs-ink" data-testid="assignment-page">
      <div className="mx-auto max-w-3xl space-y-6 px-5 py-10 sm:px-7">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-rs-muted">
            Status: {assignment.status}
            {assignment.locked ? ' · Locked' : ''}
          </p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-rs-navy">{assignment.title}</h1>
          <p className="mt-2 text-sm text-rs-body">
            Pass mark {assignment.passPercent}%
            {assignment.countsTowardCertificate ? ' · Counts toward certificate' : ''}
          </p>
        </div>

        {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : null}
        {statusMessage ? <p className="text-sm font-semibold text-rs-navy">{statusMessage}</p> : null}

        <Card className="space-y-5 p-6">
          <NarrativeBlock
            courseId={courseId}
            assignmentId={assignmentId}
            slot="instructions"
            narrative={assignment.instructions}
            heading="Instructions"
          />

          <section>
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-rs-muted">Criteria</h2>
            <ul className="space-y-1 text-sm text-rs-body">
              {assignment.criteria.map((c) => (
                <li key={c.id} className="flex justify-between gap-3 border-b border-rs-line py-2">
                  <span>{c.label}</span>
                  <span className="shrink-0 font-semibold text-rs-navy">{c.maxPoints} pts</span>
                </li>
              ))}
            </ul>
          </section>

          {(assignment.rubric.mode === 'plain' && assignment.rubric.text) ||
          assignment.rubric.mode === 'rich' ||
          assignment.rubric.mode === 'image' ? (
            <NarrativeBlock
              courseId={courseId}
              assignmentId={assignmentId}
              slot="rubric"
              narrative={assignment.rubric}
              heading="Rubric"
            />
          ) : null}
        </Card>

        {latest ? (
          <Card className="space-y-2 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wide text-rs-muted">Your latest attempt</h2>
            <p className="text-sm text-rs-body">Status: {latest.status}</p>
            {latest.status === 'graded' ? (
              <>
                <p className="text-sm text-rs-body">
                  Score: {latest.scorePercent ?? '—'}% · {latest.passed ? 'Passed' : 'Not passed'}
                </p>
                {latest.feedback != null && latest.feedback !== '' ? (
                  <p className="whitespace-pre-wrap text-sm text-rs-body" data-testid="assignment-feedback">
                    {latest.feedback}
                  </p>
                ) : null}
              </>
            ) : null}
          </Card>
        ) : null}

        {assignment.locked ? (
          <Card className="p-6">
            <p className="text-sm text-rs-body">
              This assignment is locked until earlier module quizzes must be passed.
            </p>
          </Card>
        ) : latest?.status === 'submitted' || (latest?.status === 'graded' && latest.passed) ? (
          <Card className="p-6">
            <p className="text-sm text-rs-muted">
              {latest.status === 'submitted'
                ? 'Your submission is awaiting a grade.'
                : 'You have already passed this assignment.'}
            </p>
          </Card>
        ) : (
          <Card className="p-6">
            <form className="space-y-4" onSubmit={(e) => void handleSubmit(e)}>
              <Field label="Upload file" hint={SUBMISSION_ACCEPT_HINT}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={LESSON_ATTACHMENT_ACCEPT}
                  aria-label="Upload file"
                />
              </Field>
              <Field label="Note to evaluator (optional)">
                <textarea
                  className="min-h-[88px] w-full"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  aria-label="Note to evaluator"
                  maxLength={4000}
                />
              </Field>
              <Button type="submit" disabled={busy}>
                {busy ? 'Submitting…' : 'Submit assignment'}
              </Button>
            </form>
          </Card>
        )}

        <Link to={courseId ? `/courses/${courseId}` : '/courses'} className="text-sm font-semibold text-rs-blue hover:underline">
          Back to course
        </Link>
      </div>
    </div>
  )
}
