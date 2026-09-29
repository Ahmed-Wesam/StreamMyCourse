import { jsPDF } from 'jspdf'

const INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'

export type CertificatePdfData = {
  name: string
  title: string
  cred: string
  date: string
}

/**
 * Generates a downloadable landscape A4 PDF certificate (ported from the Research Spectrum prototype).
 */
export function generateCertificatePDF(data: CertificatePdfData): void {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' })
  const W = doc.internal.pageSize.getWidth()
  const H = doc.internal.pageSize.getHeight()
  const navy: [number, number, number] = [10, 23, 51]
  const blue: [number, number, number] = [30, 94, 255]
  const muted: [number, number, number] = [113, 128, 160]
  const ink: [number, number, number] = [11, 23, 51]

  doc.setDrawColor(blue[0], blue[1], blue[2])
  doc.setLineWidth(2.5)
  doc.rect(24, 24, W - 48, H - 48)
  doc.setDrawColor(navy[0], navy[1], navy[2])
  doc.setLineWidth(0.75)
  doc.rect(34, 34, W - 68, H - 68)

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(22)
  doc.setTextColor(navy[0], navy[1], navy[2])
  doc.text('RESEARCH SPECTRUM', W / 2, 90, { align: 'center' })

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(13)
  doc.setTextColor(muted[0], muted[1], muted[2])
  doc.text('CERTIFICATE OF COMPLETION', W / 2, 122, { align: 'center' })

  doc.setFontSize(12)
  doc.text('This certificate is proudly presented to', W / 2, 165, { align: 'center' })

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(34)
  doc.setTextColor(blue[0], blue[1], blue[2])
  doc.text(data.name, W / 2, 205, { align: 'center' })

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(13)
  doc.setTextColor(ink[0], ink[1], ink[2])
  doc.text('for successfully completing the course', W / 2, 238, { align: 'center' })

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(20)
  doc.text(data.title, W / 2, 266, { align: 'center' })

  const fy = H - 90
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.setTextColor(ink[0], ink[1], ink[2])
  doc.text(data.date, 120, fy, { align: 'center' })
  doc.text(INSTRUCTOR_NAME, W / 2, fy, { align: 'center' })
  doc.text(data.cred, W - 120, fy, { align: 'center' })

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(muted[0], muted[1], muted[2])
  doc.text('Issue Date', 120, fy + 16, { align: 'center' })
  doc.text('Founder & Instructor, Research Spectrum', W / 2, fy + 16, { align: 'center' })
  doc.text('Credential ID', W - 120, fy + 16, { align: 'center' })

  doc.setDrawColor(225, 229, 242)
  doc.setLineWidth(0.75)
  doc.line(70, fy - 22, 170, fy - 22)
  doc.line(W / 2 - 90, fy - 22, W / 2 + 90, fy - 22)
  doc.line(W - 170, fy - 22, W - 70, fy - 22)

  doc.setFontSize(9)
  doc.setTextColor(muted[0], muted[1], muted[2])
  doc.text(`Verify this certificate at researchspectrum.org/verify/${data.cred}`, W / 2, H - 40, {
    align: 'center',
  })

  doc.save(`Research-Spectrum-Certificate-${data.cred}.pdf`)
}
