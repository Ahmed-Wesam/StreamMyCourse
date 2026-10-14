import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import QRCode from 'qrcode'
import { createElement, type ReactNode } from 'react'
import { flushSync } from 'react-dom'
import { createRoot } from 'react-dom/client'

import type { BundleCertificateFixture, CertificateFixture } from './certificateFixture'
import { BundleCertificateDocument } from './BundleCertificateDocument'
import { CertificateDocument } from './CertificateDocument'

const CERT_WIDTH = 1123
const CERT_HEIGHT = 794

const PDF_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya, MD'
const PDF_INSTRUCTOR_TITLE = 'Founder & Course Instructor'

type CertificatePdfData = {
  name: string
  title: string
  cred: string
  date: string
}

type BundleCertificatePdfData = {
  name: string
  cred: string
  date: string
}

function publicVerifyUrl(credentialId: string): string {
  return `https://researchspectrum.org/verify/${credentialId}`
}

function mountCaptureHost(): HTMLDivElement {
  const host = document.createElement('div')
  host.setAttribute('data-certificate-pdf-host', 'true')
  // In the viewport (not shifted off-screen). html2canvas paints white blocks
  // and drops the seal when the node sits at a large negative left.
  host.style.position = 'fixed'
  host.style.left = '0'
  host.style.top = '0'
  host.style.width = `${CERT_WIDTH}px`
  host.style.height = `${CERT_HEIGHT}px`
  host.style.zIndex = '-1'
  host.style.pointerEvents = 'none'
  host.style.background = '#ffffff'
  document.body.appendChild(host)
  return host
}

async function verifyQrDataUrl(credentialId: string): Promise<string> {
  return QRCode.toDataURL(publicVerifyUrl(credentialId), {
    errorCorrectionLevel: 'M',
    margin: 0,
    width: 200,
    color: { dark: '#0a1733', light: '#ffffff' },
  })
}

async function waitForHostImages(host: HTMLElement): Promise<void> {
  const images = Array.from(host.querySelectorAll('img'))
  await Promise.all(
    images.map(
      (img) =>
        new Promise<void>((resolve) => {
          if (img.complete) {
            resolve()
            return
          }
          const finish = () => resolve()
          img.addEventListener('load', finish, { once: true })
          img.addEventListener('error', finish, { once: true })
          window.setTimeout(finish, 100)
        }),
    ),
  )
}

async function renderCertificatePdf(node: ReactNode, filename: string): Promise<void> {
  const host = mountCaptureHost()
  const root = createRoot(host)
  flushSync(() => {
    root.render(node)
  })
  try {
    if (document.fonts?.ready) {
      await document.fonts.ready
    }
    await waitForHostImages(host)
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    })
    const target = host.querySelector('article') ?? host
    const canvas = await html2canvas(target, {
      scale: 2,
      backgroundColor: '#ffffff',
      useCORS: true,
      width: CERT_WIDTH,
      height: CERT_HEIGHT,
      windowWidth: CERT_WIDTH,
    })
    const doc = new jsPDF({
      orientation: 'landscape',
      unit: 'px',
      format: [CERT_WIDTH, CERT_HEIGHT],
    })
    doc.addImage(canvas.toDataURL('image/jpeg', 0.96), 'JPEG', 0, 0, CERT_WIDTH, CERT_HEIGHT)
    doc.save(filename)
  } finally {
    root.unmount()
    host.remove()
  }
}

export async function generateCertificatePDF(data: CertificatePdfData): Promise<void> {
  const qrSrc = await verifyQrDataUrl(data.cred)
  const certificate: CertificateFixture = {
    studentName: data.name,
    courseTitle: data.title,
    credentialId: data.cred,
    issueLabel: data.date,
    instructorName: PDF_INSTRUCTOR_NAME,
    instructorTitle: PDF_INSTRUCTOR_TITLE,
    status: 'valid',
    verifyPath: `/verify/${data.cred}`,
  }

  await renderCertificatePdf(
    createElement(CertificateDocument, { certificate, qrSrc }),
    `Research-Spectrum-Certificate-${data.cred}.pdf`,
  )
}

export async function generateBundleCertificatePDF(data: BundleCertificatePdfData): Promise<void> {
  const qrSrc = await verifyQrDataUrl(data.cred)
  const certificate: BundleCertificateFixture = {
    studentName: data.name,
    credentialId: data.cred,
    issueLabel: data.date,
    instructorName: PDF_INSTRUCTOR_NAME,
    instructorTitle: PDF_INSTRUCTOR_TITLE,
  }

  await renderCertificatePdf(
    createElement(BundleCertificateDocument, { certificate, qrSrc }),
    `Research-Spectrum-Mastery-Certificate-${data.cred}.pdf`,
  )
}
