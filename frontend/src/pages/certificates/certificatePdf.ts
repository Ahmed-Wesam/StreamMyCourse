import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import { createElement, type ReactNode } from 'react'
import { flushSync } from 'react-dom'
import { createRoot } from 'react-dom/client'

import type { BundleCertificateFixture, CertificateFixture } from './certificateFixture'
import { BundleCertificateDocument } from './BundleCertificateDocument'
import { CertificateDocument } from './CertificateDocument'

const DEFAULT_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'
const DEFAULT_INSTRUCTOR_TITLE = 'Founder & Instructor, Research Spectrum'

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

function mountOffScreenHost(): HTMLDivElement {
  const host = document.createElement('div')
  host.setAttribute('data-certificate-pdf-host', 'true')
  host.style.position = 'fixed'
  host.style.left = '-10000px'
  host.style.top = '0'
  host.style.pointerEvents = 'none'
  host.style.opacity = '0'
  document.body.appendChild(host)
  return host
}

async function renderCertificatePdf(node: ReactNode, filename: string): Promise<void> {
  const host = mountOffScreenHost()
  const root = createRoot(host)
  flushSync(() => {
    root.render(node)
  })
  try {
    if (document.fonts?.ready) {
      await document.fonts.ready
    }
    const canvas = await html2canvas(host, { scale: 2 })
    const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' })
    const pageW = doc.internal.pageSize.getWidth()
    const pageH = doc.internal.pageSize.getHeight()
    const imgData = canvas.toDataURL('image/png')
    doc.addImage(imgData, 'PNG', 0, 0, pageW, pageH)
    doc.save(filename)
  } finally {
    root.unmount()
    host.remove()
  }
}

export async function generateCertificatePDF(data: CertificatePdfData): Promise<void> {
  const certificate: CertificateFixture = {
    studentName: data.name,
    courseTitle: data.title,
    credentialId: data.cred,
    issueLabel: data.date,
    instructorName: DEFAULT_INSTRUCTOR_NAME,
    instructorTitle: DEFAULT_INSTRUCTOR_TITLE,
    status: 'valid',
    verifyPath: `/verify/${data.cred}`,
  }

  await renderCertificatePdf(
    createElement(CertificateDocument, { certificate }),
    `Research-Spectrum-Certificate-${data.cred}.pdf`,
  )
}

export async function generateBundleCertificatePDF(data: BundleCertificatePdfData): Promise<void> {
  const certificate: BundleCertificateFixture = {
    studentName: data.name,
    credentialId: data.cred,
    issueLabel: data.date,
    instructorName: DEFAULT_INSTRUCTOR_NAME,
    instructorTitle: DEFAULT_INSTRUCTOR_TITLE,
  }

  await renderCertificatePdf(
    createElement(BundleCertificateDocument, { certificate }),
    `Research-Spectrum-Mastery-Certificate-${data.cred}.pdf`,
  )
}
