/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { BundleCertificateDocument } from './BundleCertificateDocument'
import { CertificateDocument } from './CertificateDocument'
import { PATHWAY_COURSE_TITLES } from './courseCertificateMeta'
import {
  validBundleCertificate,
  validCertificate,
  xssStudentCertificate,
} from './certificateFixture'

afterEach(() => {
  cleanup()
})

describe('CertificateDocument', () => {
  it('renders course certificate fields from the valid fixture', () => {
    render(<CertificateDocument certificate={validCertificate} />)

    expect(screen.getByText(validCertificate.studentName)).toBeTruthy()
    expect(screen.getByText(validCertificate.courseTitle)).toBeTruthy()
    expect(screen.getByText(validCertificate.credentialId)).toBeTruthy()
    expect(screen.getByText(validCertificate.issueLabel)).toBeTruthy()
  })

  it.each(PATHWAY_COURSE_TITLES)('shows the correct duration line for %s', (courseTitle) => {
    const certificate = { ...validCertificate, courseTitle }
    const { container } = render(<CertificateDocument certificate={certificate} />)

    const expected =
      courseTitle === 'Research Methodology'
        ? '28 Hours · Competency-Based Assessment'
        : courseTitle === 'Statistics & SPSS'
          ? '42 Hours · Competency-Based Assessment'
          : courseTitle === 'Scientific Writing'
            ? '32 Hours · Competency-Based Assessment'
            : '38 Hours · Competency-Based Assessment'

    expect(container.textContent).toContain(expected)
  })

  it('renders XSS student name as text and never injects a script tag', () => {
    const { container } = render(<CertificateDocument certificate={xssStudentCertificate} />)

    expect(screen.getByText('<script>alert(1)</script>')).toBeTruthy()
    expect(container.innerHTML).not.toContain('<script')
  })

  it('shows the public verify URL with the credential id', () => {
    const { container } = render(<CertificateDocument certificate={validCertificate} />)

    expect(container.textContent).toContain(
      `researchspectrum.org/verify/${validCertificate.credentialId}`,
    )
  })
})

describe('BundleCertificateDocument', () => {
  it('shows Research Mastery Bundle, four course rows, and 140 total hours', () => {
    const { container } = render(<BundleCertificateDocument certificate={validBundleCertificate} />)

    expect(screen.getByText('Research Mastery Bundle')).toBeTruthy()
    expect(screen.getByText(validBundleCertificate.studentName)).toBeTruthy()

    for (const title of PATHWAY_COURSE_TITLES) {
      expect(screen.getByText(title)).toBeTruthy()
    }

    expect(container.textContent).toMatch(/140/)
    expect(container.textContent).not.toMatch(/\b65\b/)
  })

  it('shows the public verify URL with the bundle credential id', () => {
    const { container } = render(<BundleCertificateDocument certificate={validBundleCertificate} />)

    expect(container.textContent).toContain(
      `researchspectrum.org/verify/${validBundleCertificate.credentialId}`,
    )
  })
})
