import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Field } from '../../components/ui/Field'
import {
  getAssignment,
  getAssignmentSubmissionFileUrl,
  gradeAssignmentSubmission,
  listAssignmentSubmissions,
} from '../../lib/api/assignments'
import type { Assignment, AssignmentSubmissionListItem } from '../../lib/api/types'
import { usePageTitle } from '../../lib/page-title'

export default function TeacherAssignmentReviewPage() {
  usePageTitle('Review assignment')
  const { courseId: courseIdParam, assignmentId: assignmentIdParam } = useParams<{
    courseId: string
    assignmentId: string
  }>()
  const courseId = courseIdParam?.trim() ?? ''
  const assignmentId = assignmentIdParam?.trim() ?? ''

  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [submissions, setSubmissions] = useState<AssignmentSubmissionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [gradingId, setGradingId] = useState<string | null>(null)
  const [scores, setScores] = useState<Record<string, string>>({})
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!courseId || !assignmentId) {
      setError('Missing course or assignment id.')
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const [row, rows] = await Promise.all([
          getAssignment(courseId, assignmentId),
          listAssignmentSubmissions(courseId, assignmentId),
        ])
        if (!cancelled) {
          setAssignment(row)
          setSubmissions(rows)
        }
      } catch {
        if (!cancelled) {
          setAssignment(null)
          setSubmissions([])
          setError('Could not load submissions.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [courseId, assignmentId])

  const downloadFile = async (submissionId: string, fileId: string) => {
    if (!courseId || !assignmentId) return
    try {
      const { url } = await getAssignmentSubmissionFileUrl(
        courseId,
        assignmentId,
        submissionId,
        fileId,
      )
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch {
      setError('Could not download that file.')
    }
  }

  const startGrade = (submissionId: string) => {
    if (!assignment) return
    const initial: Record<string, string> = {}
    for (const c of assignment.criteria) {
      initial[c.id] = ''
    }
    setScores(initial)
    setFeedback('')
    setGradingId(submissionId)
    setError(null)
  }

  const handleGrade = async (event: FormEvent) => {
    event.preventDefault()
    if (!assignment || !gradingId || busy) return
    const parsedScores = assignment.criteria.map((c) => {
      const points = Number(scores[c.id])
      return { criterionId: c.id, points }
    })
    if (
      parsedScores.some(
        (s, i) =>
          !Number.isInteger(s.points) ||
          s.points < 0 ||
          s.points > (assignment.criteria[i]?.maxPoints ?? 0),
      )
    ) {
      setError('Enter a whole-number score within each criterion max.')
      return
    }
    const feedbackTrimmed = feedback.trim()
    if (!feedbackTrimmed) {
      setError('Enter feedback.')
      return
    }

    setBusy(true)
    setError(null)
    try {
      await gradeAssignmentSubmission(courseId, assignmentId, gradingId, {
        scores: parsedScores,
        feedback: feedbackTrimmed,
      })
      const rows = await listAssignmentSubmissions(courseId, assignmentId)
      if (mountedRef.current) {
        setSubmissions(rows)
        setGradingId(null)
        setFeedback('')
        setScores({})
      }
    } catch {
      if (mountedRef.current) setError('Could not submit grade.')
    } finally {
      if (mountedRef.current) setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-8 text-sm text-rs-muted" data-testid="teacher-assignment-review">
        Loading…
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-8" data-testid="teacher-assignment-review">
        <p className="text-sm text-red-700">{error ?? 'Assignment not found.'}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-5 py-8 text-rs-ink" data-testid="teacher-assignment-review">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-rs-navy">{assignment.title}</h1>
        <p className="mt-1 text-sm text-rs-muted">Review submissions and submit grades.</p>
      </div>

      {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : null}

      <Card className="p-6">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-rs-muted">Submissions</h2>
        {submissions.length === 0 ? (
          <p className="text-sm text-rs-muted">No submissions yet.</p>
        ) : (
          <ul className="space-y-3">
            {submissions.map((row) => (
              <li
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rs-line px-4 py-3"
              >
                <div className="text-sm text-rs-body">
                  <div className="font-semibold text-rs-navy">{row.id}</div>
                  <div>
                    Status: {row.status}
                    {row.scorePercent != null ? ` · ${row.scorePercent}%` : ''}
                    {row.passed != null ? (row.passed ? ' · Passed' : ' · Failed') : ''}
                  </div>
                  {row.note ? <div className="mt-1 text-rs-muted">Note: {row.note}</div> : null}
                  {row.files && row.files.length > 0 ? (
                    <ul className="mt-2 space-y-1">
                      {row.files
                        .filter((f) => f.status === 'ready')
                        .map((f) => (
                          <li key={f.id}>
                            <button
                              type="button"
                              className="text-left text-sm font-semibold text-rs-blue hover:underline"
                              onClick={() => void downloadFile(row.id, f.id)}
                            >
                              Download {f.title}
                            </button>
                          </li>
                        ))}
                    </ul>
                  ) : null}
                </div>
                {row.status === 'submitted' ? (
                  <Button type="button" size="sm" onClick={() => startGrade(row.id)}>
                    Grade submission
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {gradingId && assignment ? (
        <Card className="p-6">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-rs-muted">
            Grade {gradingId}
          </h2>
          <form className="space-y-4" onSubmit={(e) => void handleGrade(e)}>
            {assignment.criteria.map((c) => (
              <Field
                key={c.id}
                label={`${c.label} (max ${c.maxPoints})`}
                type="number"
                min={0}
                max={c.maxPoints}
                value={scores[c.id] ?? ''}
                onChange={(e) => setScores((prev) => ({ ...prev, [c.id]: e.target.value }))}
                aria-label={c.label}
              />
            ))}
            <Field label="Feedback">
              <textarea
                className="min-h-[100px] w-full"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                aria-label="Feedback"
                maxLength={4000}
              />
            </Field>
            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={busy}>
                {busy ? 'Submitting…' : 'Submit grade'}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setGradingId(null)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      ) : null}

      <Link
        to={courseId ? `/courses/${courseId}/assignments` : '/'}
        className="text-sm font-semibold text-rs-blue hover:underline"
      >
        Back to assignments
      </Link>
    </div>
  )
}
