import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client', () => ({
  httpGet: vi.fn(),
  httpPost: vi.fn(),
  httpPatch: vi.fn(),
  failedResponseError: vi.fn(),
}))

import { httpGet, httpPost } from './client'
import {
  completeAssignmentSubmissionFile,
  createAssignmentSubmission,
  getAssignment,
  listAssignmentSubmissions,
  listCourseAssignments,
} from './assignments'
import type { Assignment } from './types'

function sampleAssignment(id: string, moduleId: string): Assignment {
  return {
    id,
    title: `A-${id}`,
    moduleId,
    status: 'published',
    passPercent: 70,
    countsTowardCertificate: false,
    locked: false,
    instructions: { mode: 'plain', text: 'Do it' },
    rubric: { mode: 'plain', text: '' },
    criteria: [{ id: 'c1', label: 'Quality', maxPoints: 10 }],
    myLatest: null,
  }
}

describe('assignments API unwrap', () => {
  beforeEach(() => {
    vi.mocked(httpGet).mockReset()
    vi.mocked(httpPost).mockReset()
  })

  it('unwraps { assignments } and filters by moduleId when requested', async () => {
    const a1 = sampleAssignment('a1', 'm1')
    const a2 = sampleAssignment('a2', 'm2')
    vi.mocked(httpGet).mockResolvedValue({ assignments: [a1, a2] })

    const all = await listCourseAssignments('course-1')
    expect(all).toEqual([a1, a2])

    const filtered = await listCourseAssignments('course-1', { moduleId: 'm2' })
    expect(filtered).toEqual([a2])
    expect(vi.mocked(httpGet).mock.calls.at(-1)?.[0]).toContain('moduleId=m2')
  })

  it('unwraps { assignment } from get', async () => {
    const a1 = sampleAssignment('a1', 'm1')
    vi.mocked(httpGet).mockResolvedValue({ assignment: a1 })
    await expect(getAssignment('c1', 'a1')).resolves.toEqual(a1)
  })

  it('unwraps { submissions } and flattens grade from list', async () => {
    vi.mocked(httpGet).mockResolvedValue({
      submissions: [
        {
          id: 's1',
          status: 'graded',
          note: 'hi',
          grade: { scorePercent: 88, passed: true, feedback: 'Nice' },
          files: [{ id: 'f1', title: 'lab.pdf', fileType: 'pdf', byteSize: 100, status: 'ready' }],
        },
      ],
    })
    await expect(listAssignmentSubmissions('c1', 'a1')).resolves.toEqual([
      {
        id: 's1',
        status: 'graded',
        note: 'hi',
        scorePercent: 88,
        passed: true,
        feedback: 'Nice',
        files: [{ id: 'f1', title: 'lab.pdf', fileType: 'pdf', byteSize: 100, status: 'ready' }],
      },
    ])
  })

  it('unwraps { submission } from create draft', async () => {
    const draft = { id: 's1', status: 'draft' as const }
    vi.mocked(httpPost).mockResolvedValue({ submission: draft })
    await expect(createAssignmentSubmission('c1', 'a1')).resolves.toEqual(draft)
  })

  it('unwraps { file } from complete upload', async () => {
    vi.mocked(httpPost).mockResolvedValue({ file: { id: 'f1', status: 'ready' } })
    await expect(
      completeAssignmentSubmissionFile('c1', 'a1', 's1', 'f1'),
    ).resolves.toEqual({ fileId: 'f1', status: 'ready' })
  })
})
