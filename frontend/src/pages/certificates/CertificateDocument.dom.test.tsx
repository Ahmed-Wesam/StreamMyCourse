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

  it('puts the public verify URL on the QR box', () => {
    const { container } = render(<CertificateDocument certificate={validCertificate} />)

    expect(container.querySelector('[data-verify-url]')?.getAttribute('data-verify-url')).toBe(
      `https://researchspectrum.org/verify/${validCertificate.credentialId}`,
    )
    expect(container.textContent).toContain('Dr. Bahaa Aburayya, MD')
    expect(container.textContent).toContain('Founder & Course Instructor')
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

  it('puts the public verify URL on the bundle QR box', () => {
    const { container } = render(<BundleCertificateDocument certificate={validBundleCertificate} />)

    expect(container.querySelector('[data-verify-url]')?.getAttribute('data-verify-url')).toBe(
      `https://researchspectrum.org/verify/${validBundleCertificate.credentialId}`,
    )
  })
})

describe('certificate documents ignore site-wide header/footer styles', () => {
  it('render no header, footer, or aside elements', () => {
    const course = render(<CertificateDocument certificate={validCertificate} />)
    expect(course.container.querySelector('header, footer, aside')).toBeNull()
    course.unmount()

    const bundle = render(<BundleCertificateDocument certificate={validBundleCertificate} />)
    expect(bundle.container.querySelector('header, footer, aside')).toBeNull()
  })
})
