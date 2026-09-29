/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const listCourseCertificatesMock = vi.hoisted(() => vi.fn())
const revokeCourseCertificateMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/api/certificates', () => ({
  listCourseCertificates: listCourseCertificatesMock,
  revokeCourseCertificate: revokeCourseCertificateMock,
}))

import { TeacherCourseCertificates } from './TeacherCourseCertificates'

const COURSE_ID = 'course-1'
const CERT_ID = 'cert-1'
const CREDENTIAL_ID = 'RS-ABC123'

const validCertificate = {
  id: CERT_ID,
  credentialId: CREDENTIAL_ID,
  status: 'valid' as const,
  studentName: 'Ada Lovelace',
  courseTitle: 'Research Methodology',
  issueDate: 'September 2026',
}

describe('TeacherCourseCertificates', () => {
  const confirmSpy = vi.fn()

  beforeEach(() => {
    confirmSpy.mockReturnValue(true)
    Object.defineProperty(window, 'confirm', {
      configurable: true,
      writable: true,
      value: confirmSpy,
    })
    listCourseCertificatesMock.mockResolvedValue({ certificates: [validCertificate] })
    revokeCourseCertificateMock.mockResolvedValue({
      id: CERT_ID,
      credentialId: CREDENTIAL_ID,
      status: 'revoked',
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows a Revoke button for a valid certificate returned by the client', async () => {
    render(<TeacherCourseCertificates courseId={COURSE_ID} />)

    expect(await screen.findByText('Ada Lovelace')).toBeTruthy()
    expect(screen.getByText(CREDENTIAL_ID)).toBeTruthy()
    expect(screen.getByText(/September 2026/)).toBeTruthy()
    expect(screen.getByText(/valid/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /revoke/i })).toBeTruthy()
  })

  it('calls revoke client with course id and certificate id when Revoke is clicked', async () => {
    render(<TeacherCourseCertificates courseId={COURSE_ID} />)

    const revokeBtn = await screen.findByRole('button', { name: /revoke/i })
    fireEvent.click(revokeBtn)

    await waitFor(() => {
      expect(revokeCourseCertificateMock).toHaveBeenCalledWith(COURSE_ID, CERT_ID)
    })
  })

  it('hides Revoke and shows revoked status after revoke succeeds', async () => {
    render(<TeacherCourseCertificates courseId={COURSE_ID} />)

    const revokeBtn = await screen.findByRole('button', { name: /revoke/i })
    fireEvent.click(revokeBtn)

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /revoke/i })).toBeNull()
    })
    expect(screen.getByText(/revoked/i)).toBeTruthy()
  })

  it('shows empty copy when no certificates are issued', async () => {
    listCourseCertificatesMock.mockResolvedValue({ certificates: [] })

    render(<TeacherCourseCertificates courseId={COURSE_ID} />)

    expect(await screen.findByText(/no certificates issued/i)).toBeTruthy()
  })
})
