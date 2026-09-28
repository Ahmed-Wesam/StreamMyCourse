import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Field } from '../../components/ui/Field'
import {
  completeAssignmentImageUpload,
  createAssignment,
  createAssignmentImageUpload,
  patchAssignment,
  putAssignmentUpload,
} from '../../lib/api/assignments'
import { listCourseModules } from '../../lib/api/catalog'
import type { AssignmentContentMode, CourseModule } from '../../lib/api/types'
import { usePageTitle } from '../../lib/page-title'

type CriterionDraft = { key: string; label: string; maxPoints: string }

const MAX_INSTRUCTIONS_IMAGE_BYTES = 52_428_800
const ALLOWED_INSTRUCTIONS_IMAGE_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
])

function newCriterion(): CriterionDraft {
  return { key: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, label: '', maxPoints: '10' }
}

export default function TeacherAssignmentsPage() {
  usePageTitle('Assignments')
  const { courseId: courseIdParam } = useParams<{ courseId: string }>()
  const courseId = courseIdParam?.trim() ?? ''
  const navigate = useNavigate()

  const [modules, setModules] = useState<CourseModule[]>([])
  const [title, setTitle] = useState('')
  const [moduleId, setModuleId] = useState('')
  const [passPercent, setPassPercent] = useState('70')
  const [countsTowardCertificate, setCountsTowardCertificate] = useState(false)
  const [instructionsMode, setInstructionsMode] = useState<AssignmentContentMode>('plain')
  const [instructionsText, setInstructionsText] = useState('')
  const [instructionsHtml, setInstructionsHtml] = useState('')
  const [instructionsImage, setInstructionsImage] = useState<File | null>(null)
  const [criteria, setCriteria] = useState<CriterionDraft[]>([newCriterion()])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingModules, setLoadingModules] = useState(true)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!courseId) {
      setModules([])
      setLoadingModules(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        setLoadingModules(true)
        const rows = await listCourseModules(courseId)
        if (!cancelled) {
          setModules(rows)
          setModuleId((prev) => prev || rows[0]?.id || '')
        }
      } catch {
        if (!cancelled) setError('Could not load modules.')
      } finally {
        if (!cancelled) setLoadingModules(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [courseId])

  const handlePublish = async (event: FormEvent) => {
    event.preventDefault()
    if (!courseId || busy) return
    const trimmedTitle = title.trim()
    if (!trimmedTitle) {
      setError('Enter a title.')
      return
    }
    if (!moduleId) {
      setError('Choose a module.')
      return
    }
    const pass = Number(passPercent)
    if (!Number.isInteger(pass) || pass < 1 || pass > 100) {
      setError('Pass percent must be an integer from 1 to 100.')
      return
    }
    const parsedCriteria = criteria
      .map((c) => ({ label: c.label.trim(), maxPoints: Number(c.maxPoints) }))
      .filter((c) => c.label.length > 0)
    if (parsedCriteria.length === 0) {
      setError('Add at least one criterion with a label.')
      return
    }
    if (parsedCriteria.some((c) => !Number.isInteger(c.maxPoints) || c.maxPoints < 1 || c.maxPoints > 100)) {
      setError('Each criterion needs max points from 1 to 100.')
      return
    }
    if (instructionsMode === 'plain' && !instructionsText.trim()) {
      setError('Enter instructions text.')
      return
    }
    if (instructionsMode === 'rich' && !instructionsHtml.trim()) {
      setError('Enter instructions HTML.')
      return
    }
    if (instructionsMode === 'image') {
      if (!instructionsImage) {
        setError('Choose an instructions image.')
        return
      }
      if (!ALLOWED_INSTRUCTIONS_IMAGE_TYPES.has(instructionsImage.type)) {
        setError('Image must be JPEG, PNG, WebP, or GIF.')
        return
      }
      if (instructionsImage.size > MAX_INSTRUCTIONS_IMAGE_BYTES) {
        setError('Image must be 50 MiB or smaller.')
        return
      }
    }

    setBusy(true)
    setError(null)
    try {
      const created = await createAssignment(courseId, {
        title: trimmedTitle,
        moduleId,
        passPercent: pass,
        countsTowardCertificate,
      })

      if (instructionsMode === 'image' && instructionsImage) {
        await patchAssignment(courseId, created.id, { criteria: parsedCriteria })
        const { uploadUrl } = await createAssignmentImageUpload(courseId, created.id, {
          slot: 'instructions',
          contentType: instructionsImage.type,
          byteSize: instructionsImage.size,
        })
        await putAssignmentUpload(uploadUrl, instructionsImage, instructionsImage.type)
        await completeAssignmentImageUpload(courseId, created.id, 'instructions')
        await patchAssignment(courseId, created.id, { status: 'published' })
      } else {
        await patchAssignment(courseId, created.id, {
          instructions:
            instructionsMode === 'rich'
              ? { mode: 'rich', html: instructionsHtml.trim() }
              : { mode: 'plain', text: instructionsText.trim() },
          criteria: parsedCriteria,
          status: 'published',
        })
      }

      if (mountedRef.current) {
        navigate(`/courses/${courseId}/assignments/${created.id}/review`)
      }
    } catch {
      if (mountedRef.current) setError('Could not create or publish this assignment.')
    } finally {
      if (mountedRef.current) setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-5 py-8 text-rs-ink" data-testid="teacher-assignments-page">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-rs-navy">Create assignment</h1>
        <p className="mt-1 text-sm text-rs-muted">Define criteria, instructions, and publish for students.</p>
      </div>

      {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : null}

      <Card className="p-6">
        <form className="space-y-4" onSubmit={(e) => void handlePublish(e)}>
          <Field label="Title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />

          <Field label="Module">
            <select
              value={moduleId}
              onChange={(e) => setModuleId(e.target.value)}
              disabled={loadingModules}
              aria-label="Module"
            >
              {modules.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title || m.id}
                </option>
              ))}
            </select>
          </Field>

          <Field
            label="Pass percent"
            type="number"
            min={1}
            max={100}
            value={passPercent}
            onChange={(e) => setPassPercent(e.target.value)}
          />

          <label className="flex items-center gap-2 text-sm text-rs-body">
            <input
              type="checkbox"
              checked={countsTowardCertificate}
              onChange={(e) => setCountsTowardCertificate(e.target.checked)}
            />
            Counts toward certificate
          </label>

          <Field label="Instructions mode">
            <select
              value={instructionsMode}
              onChange={(e) => {
                setInstructionsMode(e.target.value as AssignmentContentMode)
                setInstructionsImage(null)
              }}
              aria-label="Instructions mode"
            >
              <option value="plain">Plain text</option>
              <option value="rich">Rich text</option>
              <option value="image">Image</option>
            </select>
          </Field>

          {instructionsMode === 'plain' ? (
            <Field label="Instructions">
              <textarea
                className="min-h-[120px] w-full"
                value={instructionsText}
                onChange={(e) => setInstructionsText(e.target.value)}
                aria-label="Instructions"
                maxLength={8000}
              />
            </Field>
          ) : null}

          {instructionsMode === 'rich' ? (
            <Field label="Instructions (HTML)">
              <textarea
                className="min-h-[120px] w-full font-mono text-sm"
                value={instructionsHtml}
                onChange={(e) => setInstructionsHtml(e.target.value)}
                aria-label="Instructions HTML"
                maxLength={8000}
              />
            </Field>
          ) : null}

          {instructionsMode === 'image' ? (
            <Field label="Instructions image">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                aria-label="Instructions image"
                onChange={(e) => {
                  const file = e.target.files?.[0] ?? null
                  setInstructionsImage(file)
                }}
              />
            </Field>
          ) : null}

          <div className="space-y-3">
            <h2 className="text-sm font-bold uppercase tracking-wide text-rs-muted">Criteria</h2>
            {criteria.map((row, index) => (
              <div key={row.key} className="grid gap-3 sm:grid-cols-[1fr_120px_auto]">
                <Field
                  label={index === 0 ? 'Label' : `Label ${index + 1}`}
                  value={row.label}
                  onChange={(e) =>
                    setCriteria((prev) =>
                      prev.map((c) => (c.key === row.key ? { ...c, label: e.target.value } : c)),
                    )
                  }
                  maxLength={120}
                />
                <Field
                  label="Max points"
                  type="number"
                  min={1}
                  max={100}
                  value={row.maxPoints}
                  onChange={(e) =>
                    setCriteria((prev) =>
                      prev.map((c) => (c.key === row.key ? { ...c, maxPoints: e.target.value } : c)),
                    )
                  }
                />
                <div className="flex items-end pb-4">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={criteria.length <= 1}
                    onClick={() => setCriteria((prev) => prev.filter((c) => c.key !== row.key))}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={criteria.length >= 12}
              onClick={() => setCriteria((prev) => [...prev, newCriterion()])}
            >
              Add criterion
            </Button>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <Button type="submit" disabled={busy || loadingModules}>
              {busy ? 'Publishing…' : 'Publish assignment'}
            </Button>
            <Button to={courseId ? `/courses/${courseId}` : '/'} variant="ghost">
              Back to course
            </Button>
          </div>
        </form>
      </Card>

      <p className="text-sm text-rs-muted">
        After publishing, open the review page to grade submissions.{' '}
        <Link to={courseId ? `/courses/${courseId}` : '/'} className="font-semibold text-rs-blue hover:underline">
          Course management
        </Link>
      </p>
    </div>
  )
}
