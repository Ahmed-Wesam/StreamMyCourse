/**
 * @vitest-environment jsdom
 */
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const listMyCertificatesMock = vi.hoisted(() => vi.fn())
const getPurchasesMock = vi.hoisted(() => vi.fn())
const listPublishedCoursesMock = vi.hoisted(() => vi.fn())
const getCourseProgressMock = vi.hoisted(() => vi.fn())
const getMyResearchTeamMock = vi.hoisted(() => vi.fn())
const generateCertificatePDFMock = vi.hoisted(() => vi.fn().mockResolvedValue(undefined))
const generateBundleCertificatePDFMock = vi.hoisted(() => vi.fn().mockResolvedValue(undefined))

vi.mock('../../lib/api/certificates', () => ({
  listMyCertificates: listMyCertificatesMock,
}))

vi.mock('../../lib/api/billing', () => ({
  getPurchases: getPurchasesMock,
}))

vi.mock('../../lib/api/public-catalog', () => ({
  listPublishedCourses: listPublishedCoursesMock,
}))

vi.mock('../../lib/api/catalog', () => ({
  getCourseProgress: getCourseProgressMock,
}))

vi.mock('../../lib/api/research-team', () => ({
  getMyResearchTeam: getMyResearchTeamMock,
}))

vi.mock('./certificatePdf', () => ({
  generateCertificatePDF: generateCertificatePDFMock,
  generateBundleCertificatePDF: generateBundleCertificatePDFMock,
}))

import CertificatesPage from '../CertificatesPage'
import { PATHWAY_COURSE_TITLES } from './courseCertificateMeta'
import { validCertificate } from './certificateFixture'

const CREDENTIAL_ID = validCertificate.credentialId
const BUNDLE_CREDENTIAL_ID = 'RS-BUNDLE-2026-MASTER01'
const PAGE_DIR = dirname(fileURLToPath(import.meta.url))
const FRONTEND_SRC = join(PAGE_DIR, '..', '..')

function pathwayCourseCertificates() {
  return PATHWAY_COURSE_TITLES.map((title, index) => ({
    id: `cert-course-${index + 1}`,
    credentialId: `RS-COURSE-${index + 1}-2026`,
    status: 'valid' as const,
    studentName: validCertificate.studentName,
    courseTitle: title,
    issueDate: validCertificate.issueLabel,
    instructorName: validCertificate.instructorName,
    instructorTitle: validCertificate.instructorTitle,
    courseId: `course-${index + 1}`,
    kind: 'course' as const,
  }))
}

function bundleCertificateRow() {
  return {
    id: 'cert-bundle-1',
    credentialId: BUNDLE_CREDENTIAL_ID,
    status: 'valid' as const,
    studentName: validCertificate.studentName,
    courseTitle: 'Research Mastery Bundle',
    issueDate: validCertificate.issueLabel,
    instructorName: validCertificate.instructorName,
    instructorTitle: validCertificate.instructorTitle,
    courseId: '',
    kind: 'bundle' as const,
  }
}

function collectTsFiles(dir: string): string[] {
  const entries = readdirSync(dir, { withFileTypes: true })
  const files: string[] = []
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === 'dist') continue
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...collectTsFiles(full))
    } else if (/\.(ts|tsx)$/.test(entry.name)) {
      files.push(full)
    }
  }
  return files
}

describe('CertificatesPage', () => {
  const writeText = vi.fn().mockResolvedValue(undefined)

  beforeEach(() => {
    generateCertificatePDFMock.mockClear()
    generateBundleCertificatePDFMock.mockClear()
    writeText.mockClear()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, origin: 'http://localhost:3000' },
    })
    getPurchasesMock.mockResolvedValue([])
    listPublishedCoursesMock.mockResolvedValue([
      { id: 'course-1', title: validCertificate.courseTitle, description: '' },
    ])
    getCourseProgressMock.mockResolvedValue({ percentComplete: 0 })
    getMyResearchTeamMock.mockResolvedValue({ courses: [] })
    listMyCertificatesMock.mockResolvedValue({
      certificates: [
        {
          id: 'cert-1',
          credentialId: CREDENTIAL_ID,
          status: 'valid',
          studentName: validCertificate.studentName,
          courseTitle: validCertificate.courseTitle,
          issueDate: validCertificate.issueLabel,
          instructorName: validCertificate.instructorName,
          instructorTitle: validCertificate.instructorTitle,
          courseId: 'course-1',
        },
      ],
      inProgress: [],
      profileIncomplete: [],
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders prototype hero and earned certificates', async () => {
    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /^your certificates$/i })).toBeTruthy()
    expect(
      screen.getByText(/verifiable proof of your research education and achievements within research spectrum/i),
    ).toBeTruthy()
    const earnedSection = await screen.findByRole('heading', { name: /earned certificates/i })
    const earnedGrid = earnedSection.closest('section')
    expect(earnedGrid).toBeTruthy()
    expect(within(earnedGrid as HTMLElement).getByText(validCertificate.courseTitle)).toBeTruthy()
    expect(within(earnedGrid as HTMLElement).getByText(validCertificate.studentName)).toBeTruthy()
  })

  it('shows empty state when there are no certificates or in-progress items', async () => {
    listMyCertificatesMock.mockResolvedValue({
      certificates: [],
      inProgress: [],
      profileIncomplete: [],
    })

    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /earn your first certificate/i })).toBeTruthy()
  })

  it('copies share link using window.location.origin + verifyPath', async () => {
    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    const copyBtn = await screen.findByRole('button', { name: /copy share link/i })
    fireEvent.click(copyBtn)

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(`http://localhost:3000/verify/${CREDENTIAL_ID}`)
    })
  })

  it('dynamically imports certificatePdf and does not statically import jspdf', () => {
    const pageSource = readFileSync(join(FRONTEND_SRC, 'pages', 'CertificatesPage.tsx'), 'utf8')
    const pdfSource = readFileSync(join(PAGE_DIR, 'certificatePdf.ts'), 'utf8')

    expect(pageSource).toMatch(/import\(\s*['"]\.\/certificates\/certificatePdf['"]\s*\)/)
    expect(pageSource).not.toMatch(/from\s+['"]jspdf['"]/)
    expect(pdfSource).toMatch(/from\s+['"]jspdf['"]/)

    const jspdfImporters = collectTsFiles(FRONTEND_SRC).filter((file) => {
      const source = readFileSync(file, 'utf8')
      return /from\s+['"]jspdf['"]|require\(\s*['"]jspdf['"]\s*\)/.test(source)
    })

    expect(jspdfImporters).toEqual([join(PAGE_DIR, 'certificatePdf.ts')])
    expect(pageSource).not.toMatch(/from\s+['"]html2canvas['"]/)
    expect(pdfSource).toMatch(/from\s+['"]html2canvas['"]|import\s+html2canvas/)
  })

  it('verify link points at /verify/{credentialId}', async () => {
    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    const verifyLink = await screen.findByRole('link', { name: /verify certificate/i })
    expect(verifyLink.getAttribute('href')).toBe(`/verify/${CREDENTIAL_ID}`)
  })

  it('counts four pathway course certificates (not bundle) in hero stats and learning hours', async () => {
    listMyCertificatesMock.mockResolvedValue({
      certificates: [...pathwayCourseCertificates(), bundleCertificateRow()],
      inProgress: [],
      profileIncomplete: [],
    })
    listPublishedCoursesMock.mockResolvedValue(
      PATHWAY_COURSE_TITLES.map((title, index) => ({
        id: `course-${index + 1}`,
        title,
        description: '',
      })),
    )

    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    const earnedHeading = await screen.findByRole('heading', { name: /earned certificates/i })
    const earnedSection = earnedHeading.closest('section')
    expect(earnedSection).toBeTruthy()
    const earnedCards = within(earnedSection as HTMLElement).getAllByRole('article')
    expect(earnedCards.length).toBe(5)

    expect(
      screen.queryByRole('heading', { name: /you've completed the full research spectrum pathway/i }),
    ).toBeNull()

    const statGrid = document.getElementById('cert-stat-section')
    expect(statGrid).toBeTruthy()
    const earnedStat = within(statGrid as HTMLElement).getByText('Certificates Earned').parentElement
    expect(earnedStat?.querySelector('.val')?.textContent).toBe('4')
    expect(earnedStat?.querySelector('.vsub')?.textContent).toBe('of 4 available')
    expect(within(statGrid as HTMLElement).getByText('Total Learning Hours').parentElement?.querySelector('.val')?.textContent).toBe(
      '140',
    )
    expect(screen.queryByText('5 of 4')).toBeNull()
  })

  it('downloads bundle mastery PDF via generateBundleCertificatePDF dynamic import', async () => {
    listMyCertificatesMock.mockResolvedValue({
      certificates: [...pathwayCourseCertificates(), bundleCertificateRow()],
      inProgress: [],
      profileIncomplete: [],
    })
    listPublishedCoursesMock.mockResolvedValue(
      PATHWAY_COURSE_TITLES.map((title, index) => ({
        id: `course-${index + 1}`,
        title,
        description: '',
      })),
    )

    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    const bundleTitle = await screen.findByRole('heading', { name: /research mastery bundle/i })
    const bundleCard = bundleTitle.closest('article')
    expect(bundleCard).toBeTruthy()

    const downloadBtn = within(bundleCard as HTMLElement).getByRole('button', { name: /download certificate/i })
    fireEvent.click(downloadBtn)

    await waitFor(() => {
      expect(generateBundleCertificatePDFMock).toHaveBeenCalledWith({
        name: validCertificate.studentName,
        cred: BUNDLE_CREDENTIAL_ID,
        date: validCertificate.issueLabel,
      })
    })
    expect(generateCertificatePDFMock).not.toHaveBeenCalled()
  })

  it('uses course-only count for PATHWAY_TOTAL eligibility (four courses, not bundle)', async () => {
    listMyCertificatesMock.mockResolvedValue({
      certificates: [...pathwayCourseCertificates(), bundleCertificateRow()],
      inProgress: [],
      profileIncomplete: [],
    })
    listPublishedCoursesMock.mockResolvedValue(
      PATHWAY_COURSE_TITLES.map((title, index) => ({
        id: `course-${index + 1}`,
        title,
        description: '',
      })),
    )

    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /you're eligible to apply/i })).toBeTruthy()
    expect(screen.queryByText(/5\/4/)).toBeNull()
    expect(screen.queryByText(/5 of 4/)).toBeNull()
  })
})
