type CertificateStatus = 'valid' | 'revoked'

export type CertificateFixture = {
  studentName: string
  courseTitle: string
  credentialId: string
  issueLabel: string
  instructorName: string
  instructorTitle: string
  status: CertificateStatus
  verifyPath: string
}

export type CertificateNotFoundFixture = {
  status: 'not_found'
  credentialId?: string
}

export type CertificateInProgressFixture = {
  courseTitle: string
  passedCount: number
  totalCount: number
}

export type CertificateProfileIncompleteFixture = {
  courseTitle: string
  requirementsMet: true
  message: string
  href: string
}

const CREDENTIAL_ID = 'RS-A1B7F3-2026-9C2E10B4D8'
const VERIFY_PATH = `/verify/${CREDENTIAL_ID}`

const baseCertificate = {
  courseTitle: 'Research Methodology',
  credentialId: CREDENTIAL_ID,
  issueLabel: 'September 2026',
  instructorName: 'Dr. Bahaa Aburayya',
  instructorTitle: 'Founder & Instructor, Research Spectrum',
  verifyPath: VERIFY_PATH,
} as const

export const validCertificate: CertificateFixture = {
  ...baseCertificate,
  studentName: 'Ada Lovelace',
  status: 'valid',
}

export const xssStudentCertificate: CertificateFixture = {
  ...baseCertificate,
  studentName: '<script>alert(1)</script>',
  status: 'valid',
}

export const revokedCertificate: CertificateFixture = {
  ...baseCertificate,
  studentName: 'Ada Lovelace',
  status: 'revoked',
}

export const notFoundCertificate: CertificateNotFoundFixture = {
  status: 'not_found',
  credentialId: 'RS-UNKNOWN-0000',
}

export const inProgressCertificate: CertificateInProgressFixture = {
  courseTitle: 'Research Methodology',
  passedCount: 1,
  totalCount: 2,
}

export const profileIncompleteCertificate: CertificateProfileIncompleteFixture = {
  courseTitle: 'Research Methodology',
  requirementsMet: true,
  message: 'Add your profile name to issue this certificate.',
  href: '/account/profile',
}
