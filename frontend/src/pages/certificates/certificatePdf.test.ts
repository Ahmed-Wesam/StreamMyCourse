/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const html2canvasMock = vi.hoisted(() => vi.fn())
const jsPDFCtorMock = vi.hoisted(() => vi.fn())
vi.mock('html2canvas', () => ({
  default: html2canvasMock,
}))

vi.mock('jspdf', () => ({
  jsPDF: jsPDFCtorMock,
}))

vi.mock('qrcode', () => ({
  default: {
    toDataURL: vi.fn(async () => 'data:image/png;base64,qr'),
  },
}))

import { generateBundleCertificatePDF, generateCertificatePDF } from './certificatePdf'

const CRED = 'RS-A1B7F3-2026-9C2E10B4D8'
const BUNDLE_CRED = 'RS-BUNDLE-2026-MASTER01'
const VERIFY_HTTPS = `https://researchspectrum.org/verify/${CRED}`
const BUNDLE_VERIFY_HTTPS = `https://researchspectrum.org/verify/${BUNDLE_CRED}`

function makeJsPdfInstance() {
  const addImage = vi.fn()
  const save = vi.fn()
  const pageSize = { getWidth: () => 842, getHeight: () => 595 }
  return {
    internal: { pageSize },
    addImage,
    save,
  }
}

describe('certificatePdf', () => {
  let capturedHost: HTMLElement | null = null

  beforeEach(() => {
    capturedHost = null
    html2canvasMock.mockReset()
    jsPDFCtorMock.mockReset()

    html2canvasMock.mockImplementation(async (host: HTMLElement) => {
      capturedHost = host
      return {
        toDataURL: () => 'data:image/png;base64,abc',
        width: 1123,
        height: 794,
      }
    })

    jsPDFCtorMock.mockImplementation(function JsPDFMock() {
      return makeJsPdfInstance()
    })
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('generateCertificatePDF captures a course document with the https verify URL', async () => {
    await generateCertificatePDF({
      name: 'Ada Lovelace',
      title: 'Research Methodology',
      cred: CRED,
      date: 'September 2026',
    })

    expect(jsPDFCtorMock).toHaveBeenCalledWith({
      orientation: 'landscape',
      unit: 'px',
      format: [1123, 794],
    })

    expect(html2canvasMock).toHaveBeenCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({
        scale: 2,
        backgroundColor: '#ffffff',
        useCORS: true,
        width: 1123,
        height: 794,
        windowWidth: 1123,
      }),
    )
    expect(capturedHost?.querySelector('[data-verify-url]')?.getAttribute('data-verify-url')).toBe(
      VERIFY_HTTPS,
    )
    expect(capturedHost?.querySelector('.certificate-document__qr img')?.getAttribute('src')).toBe(
      'data:image/png;base64,qr',
    )

    const doc = jsPDFCtorMock.mock.results[0]?.value
    expect(doc?.addImage).toHaveBeenCalled()
    expect(doc?.save).toHaveBeenCalledWith(`Research-Spectrum-Certificate-${CRED}.pdf`)
  })

  it('generateBundleCertificatePDF captures a mastery bundle document with bundle credential', async () => {
    await generateBundleCertificatePDF({
      name: 'Ada Lovelace',
      cred: BUNDLE_CRED,
      date: 'September 2026',
    })

    expect(html2canvasMock).toHaveBeenCalled()

    expect(capturedHost?.querySelector('[data-verify-url]')?.getAttribute('data-verify-url')).toBe(
      BUNDLE_VERIFY_HTTPS,
    )
    expect(capturedHost?.textContent).toContain('Research Mastery Bundle')

    const doc = jsPDFCtorMock.mock.results[0]?.value
    expect(doc?.save).toHaveBeenCalledWith(`Research-Spectrum-Mastery-Certificate-${BUNDLE_CRED}.pdf`)
  })

  it('removes the off-screen host element after a successful capture', async () => {
    await generateCertificatePDF({
      name: 'Ada Lovelace',
      title: 'Research Methodology',
      cred: CRED,
      date: 'September 2026',
    })

    const hosts = document.querySelectorAll('[data-certificate-pdf-host]')
    expect(hosts.length).toBe(0)
  })

  it('removes the host element when html2canvas throws', async () => {
    html2canvasMock.mockRejectedValueOnce(new Error('capture failed'))

    await expect(
      generateCertificatePDF({
        name: 'Ada Lovelace',
        title: 'Research Methodology',
        cred: CRED,
        date: 'September 2026',
      }),
    ).rejects.toThrow('capture failed')

    const hosts = document.querySelectorAll('[data-certificate-pdf-host]')
    expect(hosts.length).toBe(0)
  })
})
