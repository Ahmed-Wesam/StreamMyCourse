/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client', () => ({
  httpGet: vi.fn(),
  httpPost: vi.fn(),
}))

import { httpGet } from './client'
import { listMyCertificates } from './certificates'

describe('listMyCertificates', () => {
  beforeEach(() => {
    vi.mocked(httpGet).mockReset()
  })

  it('normalizes bundle kind with empty courseId', async () => {
    vi.mocked(httpGet).mockResolvedValue({
      certificates: [
        {
          id: 'bundle-cert-1',
          credentialId: 'RS-BUNDLE-2026-MASTER01',
          status: 'valid',
          studentName: 'Ada Lovelace',
          courseTitle: 'Research Mastery Bundle',
          issueDate: 'September 2026',
          instructorName: 'Dr. Bahaa Aburayya',
          instructorTitle: 'Founder & Instructor, Research Spectrum',
          courseId: '',
          kind: 'bundle',
        },
      ],
      inProgress: [],
      profileIncomplete: [],
    })

    const result = await listMyCertificates()

    expect(result.certificates).toHaveLength(1)
    expect(result.certificates[0]).toMatchObject({
      id: 'bundle-cert-1',
      credentialId: 'RS-BUNDLE-2026-MASTER01',
      courseId: '',
      kind: 'bundle',
      courseTitle: 'Research Mastery Bundle',
    })
  })
})
