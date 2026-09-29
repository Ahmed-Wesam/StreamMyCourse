/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { CertificateCard } from './CertificateCard'
import { CertificateProgressCard } from './CertificateProgressCard'
import { CertificateVerifyDocument } from './CertificateVerifyDocument'
import {
  inProgressCertificate,
  notFoundCertificate,
  profileIncompleteCertificate,
  revokedCertificate,
  validCertificate,
  xssStudentCertificate,
} from './certificateFixture'

afterEach(() => {
  cleanup()
})

describe('CertificateViews', () => {
  it('earned card shows course title, student name, credential id, and issue label', () => {
    const { container } = render(
      <MemoryRouter>
        <CertificateCard certificate={validCertificate} />
      </MemoryRouter>,
    )

    expect(screen.getByText(validCertificate.courseTitle)).toBeTruthy()
    expect(screen.getByText(validCertificate.studentName)).toBeTruthy()
    expect(screen.getByText(validCertificate.credentialId)).toBeTruthy()
    expect(screen.getAllByText(validCertificate.issueLabel).length).toBeGreaterThan(0)
    expect(container.textContent).toContain('Certificate of Completion')
  })

  it('renders XSS student name as text and never as a script tag', () => {
    const { container } = render(
      <MemoryRouter>
        <CertificateCard certificate={xssStudentCertificate} />
      </MemoryRouter>,
    )

    expect(screen.getByText('<script>alert(1)</script>')).toBeTruthy()
    expect(container.innerHTML).not.toContain('<script')
  })

  it('revoked card or verify result shows revoked status and the student name', () => {
    render(
      <MemoryRouter>
        <CertificateCard certificate={revokedCertificate} />
        <CertificateVerifyDocument certificate={revokedCertificate} />
      </MemoryRouter>,
    )

    expect(screen.getAllByText(/revoked/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(revokedCertificate.studentName).length).toBeGreaterThan(0)
  })

  it('not-found result does not show a student name from the valid fixture', () => {
    render(<CertificateVerifyDocument result={notFoundCertificate} />)

    expect(screen.getAllByText(/not found/i).length).toBeGreaterThan(0)
    expect(screen.queryByText(validCertificate.studentName)).toBeNull()
  })

  it('in-progress card shows the fraction (1 of 2)', () => {
    render(<CertificateProgressCard progress={inProgressCertificate} />)

    expect(screen.getByText(/1 of 2/i)).toBeTruthy()
    expect(screen.getByText(inProgressCertificate.courseTitle)).toBeTruthy()
  })

  it('profile-incomplete state links to /account/profile', () => {
    render(
      <MemoryRouter>
        <CertificateProgressCard incomplete={profileIncompleteCertificate} />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /profile/i })
    expect(link.getAttribute('href')).toBe('/account/profile')
    expect(screen.getByText(profileIncompleteCertificate.message)).toBeTruthy()
  })
})
