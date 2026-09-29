/**
 * @vitest-environment jsdom
 */
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const listMyCertificatesMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/api/certificates', () => ({
  listMyCertificates: listMyCertificatesMock,
}))

import CertificatesPage from '../CertificatesPage'
import { validCertificate } from './certificateFixture'

const CREDENTIAL_ID = validCertificate.credentialId
const PAGE_DIR = dirname(fileURLToPath(import.meta.url))
const FRONTEND_SRC = join(PAGE_DIR, '..', '..')

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
    writeText.mockClear()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, origin: 'http://localhost:3000' },
    })
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

  it('renders a certificates heading with earned certificates', async () => {
    render(
      <MemoryRouter>
        <CertificatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /certificates/i })).toBeTruthy()
    expect(await screen.findByText(validCertificate.courseTitle)).toBeTruthy()
    expect(screen.getByText(validCertificate.studentName)).toBeTruthy()
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

    expect(await screen.findByText(/no certificates yet/i)).toBeTruthy()
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
})
