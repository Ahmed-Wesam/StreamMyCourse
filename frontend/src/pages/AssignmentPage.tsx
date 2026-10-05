import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { usePageReveal } from '../components/auth/usePageReveal'
import { SafeRichText } from '../components/assignments/SafeRichText'
import { getCourse } from '../lib/api/catalog'
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
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import { contentTypeForLessonFileType, fileTypeFromFileName, LESSON_ATTACHMENT_ACCEPT } from '../lib/lessonFileType'
import { usePageTitle } from '../lib/page-title'
import {
  ASSIGNMENT_CHECKLIST_ITEMS,
  ASSIGNMENT_FAQ_ITEMS,
  ASSIGNMENT_RESOURCE_CARDS,
  BRIEF_DELIVERABLES,
  BRIEF_OBJECTIVES,
} from './assignment/assignmentPrototypeCopy'
import './AssignmentPage.css'

const SUBMISSION_MAX_BYTES = 100 * 1024 * 1024

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function NarrativeBlock({
  courseId,
  assignmentId,
  slot,
  narrative,
}: {
  courseId: string
  assignmentId: string
  slot: 'instructions' | 'rubric'
  narrative: AssignmentNarrative
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

  if (narrative.mode === 'plain' && narrative.text) {
    return <p className="brief-desc">{narrative.text}</p>
  }
  if (narrative.mode === 'rich' && narrative.html) {
    return <SafeRichText className="brief-desc" html={narrative.html} />
  }
  if (narrative.mode === 'image') {
    return imageUrl ? (
      <img src={imageUrl} alt="" className="asgn-narrative-image" />
    ) : (
      <p className="brief-desc">Image unavailable.</p>
    )
  }
  return null
}

function statusPillFor(assignment: Assignment): { className: string; label: string } {
  const latest = assignment.myLatest
  if (assignment.locked) return { className: 'asgn-pill ap-not-started', label: 'Locked' }
  if (!latest) return { className: 'asgn-pill ap-in-progress', label: 'In Progress' }
  if (latest.status === 'submitted') return { className: 'asgn-pill ap-submitted', label: 'Submitted' }
  if (latest.status === 'graded' && latest.passed) return { className: 'asgn-pill ap-passed', label: 'Passed' }
  if (latest.status === 'graded') return { className: 'asgn-pill ap-revision', label: 'Revision Requested' }
  return { className: 'asgn-pill ap-in-progress', label: 'In Progress' }
}

function certificateBandPercent(assignment: Assignment): number {
  if (assignment.myLatest?.status === 'graded' && assignment.myLatest.passed) return 100
  if (assignment.myLatest?.status === 'submitted') return 90
  if (assignment.locked) return 40
  return 80
}

function canUpload(assignment: Assignment): boolean {
  if (assignment.locked) return false
  const latest = assignment.myLatest
  if (!latest) return true
  if (latest.status === 'submitted') return false
  if (latest.status === 'graded' && latest.passed) return false
  return true
}

function showSubmittedPanel(assignment: Assignment): boolean {
  const latest = assignment.myLatest
  return latest?.status === 'submitted'
}

function showPassedPanel(assignment: Assignment): boolean {
  const latest = assignment.myLatest
  return latest?.status === 'graded' && Boolean(latest.passed)
}

export default function AssignmentPage() {
  usePageTitle('Assignment')
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const { courseId: courseIdParam, assignmentId: assignmentIdParam } = useParams<{
    courseId: string
    assignmentId: string
  }>()
  const courseId = courseIdParam?.trim() ?? ''
  const assignmentId = assignmentIdParam?.trim() ?? ''

  const [courseTitle, setCourseTitle] = useState('Course')
  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [submitModalOpen, setSubmitModalOpen] = useState(false)
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [checklistChecked, setChecklistChecked] = useState<boolean[]>(() =>
    ASSIGNMENT_CHECKLIST_ITEMS.map(() => false),
  )
  const [faqOpen, setFaqOpen] = useState<number | null>(null)
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
        const [row, course] = await Promise.all([
          getAssignment(courseId, assignmentId),
          getCourse(courseId).catch(() => null),
        ])
        if (!cancelled) {
          setAssignment(row)
          if (course?.title) setCourseTitle(course.title)
        }
      } catch (err) {
        if (!cancelled) {
          setAssignment(null)
          setError(catalogApiUserMessage(err, 'loadAssignment'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [courseId, assignmentId])

  const runSubmit = async () => {
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
        setSelectedFileName(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
        setSubmitModalOpen(false)
        setStatusMessage('Submission sent.')
      }
    } catch (err) {
      if (mountedRef.current) setError(catalogApiUserMessage(err, 'submitAssignment'))
    } finally {
      if (mountedRef.current) setBusy(false)
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setSubmitModalOpen(true)
  }

  const handleConfirmSubmit = () => {
    void runSubmit()
  }

  const toggleChecklist = (index: number) => {
    setChecklistChecked((prev) => prev.map((v, i) => (i === index ? !v : v)))
  }

  const checklistDone = checklistChecked.filter(Boolean).length

  if (loading) {
    return (
      <div className="pg-assignment" data-testid="assignment-page">
        <p className="asgn-loading">Loading assignment…</p>
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="pg-assignment" data-testid="assignment-page">
        <div className="wrap">
          <p className="asgn-error" role="alert">
            {error ?? 'Assignment not found.'}
          </p>
          <Link to={courseId ? `/courses/${courseId}` : '/courses'} className="btn btn-ghost">
            Back to course
          </Link>
        </div>
      </div>
    )
  }

  const pill = statusPillFor(assignment)
  const bandPct = certificateBandPercent(assignment)
  const uploadOpen = canUpload(assignment)
  const latest = assignment.myLatest
  const passLabel = `${assignment.passPercent}% to Pass`

  return (
    <div className="pg-assignment" ref={rootRef} data-testid="assignment-page">
      <div className="asgn-breadcrumb-bar">
        <div className="wrap">
          <div className="asgn-crumb">
            <Link to="/dashboard">Dashboard</Link>
            <ChevronRightIcon />
            <Link to={courseId ? `/courses/${courseId}` : '/courses'}>{courseTitle}</Link>
            <ChevronRightIcon />
            <span className="cur">{assignment.title}</span>
          </div>
        </div>
      </div>

      {error ? (
        <p className="asgn-error" role="alert">
          {error}
        </p>
      ) : null}
      {statusMessage ? <p className="asgn-status-msg">{statusMessage}</p> : null}

      <section className="asgn-hero">
        <div className="wrap">
          <div className="asgn-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">
                <span className="dot" aria-hidden />
                Final Assessment
              </div>
              <h1>
                Final Assignment
                <br />
                <span className="g">Submission</span>
              </h1>
              <p className="sub">
                Demonstrate your ability to apply what you have learned. Successfully completing the final assignment is
                required before a course certificate can be awarded.
              </p>
              <div className="hero-meta">
                <span className="hero-meta-pill">
                  <CheckIcon />
                  {passLabel}
                </span>
                <span className="hero-meta-pill">2–4 Hours</span>
                <span className="hero-meta-pill">Unlimited Revisions</span>
              </div>
              <span className={pill.className}>{pill.label}</span>
            </div>
            <div className="overview-card">
              <p className="ov-title">Assignment Overview</p>
              <div className="ov-row">
                <span className="ov-label">Course</span>
                <span className="ov-val">{courseTitle}</span>
              </div>
              <div className="ov-row">
                <span className="ov-label">Assessment Type</span>
                <span className="ov-val">Final Competency</span>
              </div>
              <div className="ov-row">
                <span className="ov-label">Passing Requirement</span>
                <span className="ov-val">{assignment.passPercent}%</span>
              </div>
              <div className="ov-row">
                <span className="ov-label">Estimated Completion</span>
                <span className="ov-val">2–4 Hours</span>
              </div>
              <div className="ov-row">
                <span className="ov-label">Attempts</span>
                <span className="ov-val">Unlimited revisions after feedback</span>
              </div>
              <div className="ov-row">
                <span className="ov-label">Certificate Status</span>
                <span className="ov-val">
                  {latest?.status === 'graded' && latest.passed ? (
                    <span className="ov-cert-avail">Available</span>
                  ) : (
                    <span className="ov-cert-lock">Not Yet Available</span>
                  )}
                </span>
              </div>
              {latest?.status === 'graded' && latest.scorePercent != null ? (
                <div className="ov-row">
                  <span className="ov-label">Your Score</span>
                  <span className="ov-val">{latest.scorePercent}%</span>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      <div className="asgn-band">
        <div className="wrap">
          <p className="kicker" style={{ textAlign: 'center' }}>
            Certificate Readiness
          </p>
          <div className="asgn-band-pct">{bandPct}%</div>
          <p className="asgn-band-pct-sub">of certificate requirements complete</p>
          <div className="asgn-band-bar-wrap">
            <div className="asgn-band-bar" style={{ width: `${bandPct}%` }} />
          </div>
          <p className="asgn-band-label">
            {assignment.locked
              ? 'Complete and pass earlier module quizzes to unlock this assignment.'
              : `All module quizzes complete — pass the final assignment to unlock your ${courseTitle} Certificate`}
          </p>
          <div className="asgn-steps">
            <div className={`asgn-step ${assignment.locked ? 'as-cur' : 'as-done'}`}>
              <div className="asgn-step-node">
                <CheckIcon />
              </div>
              <div className="asgn-step-lbl">{assignment.locked ? 'In Progress' : 'Complete'}</div>
              <div className="asgn-step-name">Module Quizzes</div>
            </div>
            <div className={`asgn-step ${assignment.locked ? 'as-up' : latest?.passed ? 'as-done' : 'as-cur'}`}>
              <div className="asgn-step-node">
                <CheckIcon />
              </div>
              <div className="asgn-step-lbl">{latest?.passed ? 'Complete' : 'In Progress'}</div>
              <div className="asgn-step-name">Final Assignment</div>
            </div>
            <div className={`asgn-step ${latest?.passed ? 'as-cur' : 'as-up'}`}>
              <div className="asgn-step-node">
                <CheckIcon />
              </div>
              <div className="asgn-step-lbl">Upcoming</div>
              <div className="asgn-step-name">Certificate</div>
            </div>
          </div>
        </div>
      </div>

      <section className="sec" id="brief">
        <div className="wrap">
          <div className="brief-card reveal">
            <div className="brief-card-head">
              <div>
                <p className="brief-eyebrow">
                  {courseTitle} · Final Assignment
                </p>
                <h2 className="brief-title">{assignment.title}</h2>
              </div>
              <span className={pill.className}>{pill.label}</span>
            </div>
            <NarrativeBlock
              courseId={courseId}
              assignmentId={assignmentId}
              slot="instructions"
              narrative={assignment.instructions}
            />
            <div className="brief-grid">
              <div className="brief-col">
                <h3>Deliverables</h3>
                <ul className="brief-list">
                  {BRIEF_DELIVERABLES.map((item) => (
                    <li key={item}>
                      <span className="bi bi-ok">
                        <CheckIcon />
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="brief-col">
                <h3>Learning Objectives</h3>
                <ul className="brief-list">
                  {BRIEF_OBJECTIVES.map((item) => (
                    <li key={item}>
                      <span className="bi bi-ok">
                        <CheckIcon />
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="brief-col">
                <h3>Passing Criteria</h3>
                <ul className="brief-list">
                  {assignment.criteria.map((c) => (
                    <li key={c.id}>
                      <span className="bi bi-ok">
                        <CheckIcon />
                      </span>
                      {c.label} ({c.maxPoints} pts)
                    </li>
                  ))}
                  <li>
                    <span className="bi bi-ok">
                      <CheckIcon />
                    </span>
                    Rubric score of {assignment.passPercent}% or higher
                  </li>
                </ul>
                <div className="brief-criteria-badge">
                  <CheckIcon />
                  Minimum {assignment.passPercent}% required to pass
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="sec asgn-resources-sec">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Download Materials</p>
            <h2 className="title">Assignment Resources</h2>
          </div>
          <div className="resource-grid reveal">
            {ASSIGNMENT_RESOURCE_CARDS.map((card) => (
              <div className="resource-card" key={card.name}>
                <div className="rc-name">{card.name}</div>
                <div className="rc-desc">{card.desc}</div>
                <button type="button" className="rc-btn" disabled title="Downloads are not wired in the MVP app">
                  {card.action}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sec asgn-checklist-sec" id="checklist">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Pre-Flight Check</p>
            <h2 className="title">Before You Submit</h2>
            <p className="checklist-intro">
              Review each item before uploading. Tick each box to confirm. Complete, well-prepared proposals receive
              faster evaluations.
            </p>
          </div>
          <div className="cl-card reveal">
            <ul className="cl-list">
              {ASSIGNMENT_CHECKLIST_ITEMS.map((item, index) => (
                <li
                  key={item.title}
                  className={checklistChecked[index] ? 'cl-item checked' : 'cl-item'}
                >
                  <button
                    type="button"
                    className="cl-item-btn"
                    onClick={() => toggleChecklist(index)}
                    aria-pressed={checklistChecked[index]}
                  >
                    <span className="cl-node" aria-hidden />
                    <span className="cl-text">
                      <b>{item.title}</b>
                      <span>{item.detail}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="cl-footer">
              <span>
                {checklistDone} of {ASSIGNMENT_CHECKLIST_ITEMS.length} items confirmed
              </span>
              <a href="#submit" className="btn btn-primary btn-sm">
                Go to Submission Portal
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="sec asgn-submit-sec" id="submit">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Submit Your Work</p>
            <h2 className="title">Assignment Submission</h2>
          </div>
          <div className="portal-grid">
            <div className="portal-card reveal">
              <h3 className="pc-title">Submission Portal</h3>
              <p className="pc-sub">Upload your completed work. Ensure all required deliverables are included before submitting.</p>

              {assignment.locked ? (
                <p className="asgn-locked-note">This assignment is locked until earlier module quizzes must be passed.</p>
              ) : null}

              {!assignment.locked ? (
              <div className={`submit-panel ${uploadOpen ? 'visible' : ''}`} id="panelUpload">
                <form onSubmit={handleSubmit}>
                  <p className="support-label">Primary Submission — Required</p>
                  <div className="drop-zone">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={LESSON_ATTACHMENT_ACCEPT}
                      aria-label="Upload primary file"
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        setSelectedFileName(f?.name ?? null)
                      }}
                    />
                    <div className="dz-title">Drag &amp; drop your file here</div>
                    <div className="dz-sub">
                      <b>Browse files</b> · PDF, DOCX, ZIP
                    </div>
                  </div>
                  {selectedFileName ? (
                    <div className="file-list">
                      <div className="file-item">
                        <div className="fi-info">
                          <div className="fi-name">{selectedFileName}</div>
                        </div>
                      </div>
                    </div>
                  ) : null}
                  <div className="field asgn-note-field">
                    <label htmlFor="commentBox">
                      Notes to Evaluator <span className="optional">(optional)</span>
                    </label>
                    <textarea
                      id="commentBox"
                      placeholder="Add any context, questions, or notes for the evaluator reviewing your submission…"
                      rows={3}
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      maxLength={4000}
                    />
                  </div>
                  <div className="asgn-submit-actions">
                    <button type="submit" className="btn btn-primary" disabled={busy || !selectedFileName}>
                      {busy ? 'Submitting…' : 'Submit Assignment'}
                    </button>
                    {!selectedFileName ? (
                      <span className="submit-hint">Upload your primary file first</span>
                    ) : null}
                  </div>
                  {latest?.status === 'graded' && !latest.passed ? (
                    <p className="revision-note">
                      <strong>Revision Required</strong> — Please address the evaluator&apos;s feedback before
                      resubmitting.
                    </p>
                  ) : null}
                </form>
              </div>
              ) : null}

              <div className={`submit-panel ${showSubmittedPanel(assignment) ? 'visible' : ''}`}>
                <div className="sp-status-card">
                  <div className="sp-sc-title">Assignment Submitted</div>
                  <p className="sp-sc-body">Your assignment has been received and is awaiting evaluation.</p>
                </div>
              </div>

              <div className={`submit-panel ${showPassedPanel(assignment) ? 'visible' : ''}`}>
                <div className="sp-status-card success">
                  <div className="sp-sc-title">Assignment Passed</div>
                  <p className="sp-sc-body">
                    Congratulations — your assignment has been graded and has passed. Your course certificate is now
                    available.
                  </p>
                </div>
                <div className="asgn-passed-actions">
                  <Link to="/certificates" className="btn btn-primary btn-sm">
                    View Certificate
                  </Link>
                  <Link to="/dashboard" className="btn btn-ghost btn-sm">
                    Back to Dashboard
                  </Link>
                </div>
              </div>
            </div>

            <div className="wf-card reveal">
              <h3 className="pc-title">Evaluator Status</h3>
              <div className="wf-list">
                <div className={`wf-step ${latest ? 'wfs-done' : uploadOpen ? 'wfs-cur' : 'wfs-up'}`}>
                  <div className="wf-info">
                    <div className="wf-name">Submission received</div>
                  </div>
                </div>
                <div
                  className={`wf-step ${
                    latest?.status === 'submitted' ? 'wfs-cur' : latest?.status === 'graded' ? 'wfs-done' : 'wfs-up'
                  }`}
                >
                  <div className="wf-info">
                    <div className="wf-name">Under review</div>
                  </div>
                </div>
                <div className={`wf-step ${latest?.status === 'graded' ? 'wfs-done' : 'wfs-up'}`}>
                  <div className="wf-info">
                    <div className="wf-name">Feedback ready</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {latest?.status === 'graded' && latest.feedback ? (
        <section className="sec">
          <div className="wrap">
            <div className="sec-head reveal">
              <p className="kicker">Evaluator Assessment</p>
              <h2 className="title" style={{ fontSize: '22px' }}>
                Feedback
              </h2>
            </div>
            <div className="fb-notes reveal">
              <p data-testid="assignment-feedback">{latest.feedback}</p>
            </div>
          </div>
        </section>
      ) : null}

      <section className="sec asgn-rubric-sec" id="rubric">
        <div className="wrap">
          <div className="sec-head reveal">
            <p className="kicker">Grading</p>
            <h2 className="title">Grading Rubric</h2>
            <p className="rubric-intro">
              Your submission is evaluated across competency areas. Each area must demonstrate required proficiency to
              achieve a passing score.
            </p>
          </div>
          <div className="rubric-card reveal">
            <div className="rubric-list">
              {assignment.criteria.map((c) => (
                <div className="rubric-row" key={c.id}>
                  <div className="rb-name">{c.label}</div>
                  <div className="rb-weight">{c.maxPoints} pts</div>
                  <div className="rb-score">
                    {latest?.status === 'graded' && latest.scorePercent != null ? `${latest.scorePercent}%` : '—'}
                  </div>
                </div>
              ))}
            </div>
            {(assignment.rubric.mode === 'plain' && assignment.rubric.text) ||
            assignment.rubric.mode === 'rich' ||
            assignment.rubric.mode === 'image' ? (
              <div className="asgn-rubric-narrative">
                <NarrativeBlock
                  courseId={courseId}
                  assignmentId={assignmentId}
                  slot="rubric"
                  narrative={assignment.rubric}
                />
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="sec asgn-faq-sec">
        <div className="wrap">
          <div className="sec-head reveal" style={{ textAlign: 'center' }}>
            <p className="kicker">Help &amp; Guidance</p>
            <h2 className="title">Frequently Asked Questions</h2>
          </div>
          <div className="rt-faq-list reveal">
            {ASSIGNMENT_FAQ_ITEMS.map((item, index) => {
              const open = faqOpen === index
              return (
                <div key={item.q} className={open ? 'rt-faq-item open' : 'rt-faq-item'}>
                  <button
                    type="button"
                    className="rt-faq-q"
                    aria-expanded={open}
                    onClick={() => setFaqOpen(open ? null : index)}
                  >
                    <h3>{item.q}</h3>
                    <div className="rt-faq-ic" aria-hidden>
                      +
                    </div>
                  </button>
                  <div className="rt-faq-a">
                    <p>{item.a}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      <section className="sec asgn-cta-sec">
        <div className="wrap">
          <div className="rt-cta reveal">
            <p className="kicker cta-kicker">One Step Closer</p>
            <h2>Submit Your Assignment</h2>
            <p>Upload your completed proposal and earn your course certificate.</p>
            <div className="btn-w">
              <a href="#submit" className="btn btn-white">
                Go to Submission Portal
              </a>
              <a href="#rubric" className="btn btn-ghost cta-ghost">
                View Grading Rubric
              </a>
            </div>
          </div>
        </div>
      </section>

      {submitModalOpen ? (
        <div
          className="modal-overlay open"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modalSubmitTitle"
          onClick={() => !busy && setSubmitModalOpen(false)}
          onKeyDown={(e) => {
            if (e.key === 'Escape' && !busy) setSubmitModalOpen(false)
          }}
        >
          <div
            className="modal-box"
            role="presentation"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="modal-close-btn"
              aria-label="Close"
              onClick={() => !busy && setSubmitModalOpen(false)}
            >
              ×
            </button>
            <h3 id="modalSubmitTitle">Submit Assignment?</h3>
            <p>
              Your file will be submitted for evaluation. Ensure all required deliverables are included. Once submitted,
              your file cannot be changed until feedback is provided.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" disabled={busy} onClick={handleConfirmSubmit}>
                {busy ? 'Submitting…' : 'Confirm Submission'}
              </button>
              <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => setSubmitModalOpen(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
