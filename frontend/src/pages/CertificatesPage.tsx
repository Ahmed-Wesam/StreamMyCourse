import { useCallback, useEffect, useState } from 'react'

import { Button } from '../components/ui/Button'
import { listMyCertificates, type MeCertificatesResponse } from '../lib/api/certificates'
import { usePageTitle } from '../lib/page-title'
import { CertificateCard } from './certificates/CertificateCard'
import { CertificateProgressCard } from './certificates/CertificateProgressCard'
import type { CertificateFixture } from './certificates/certificateFixture'

const DEFAULT_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'
const DEFAULT_INSTRUCTOR_TITLE = 'Founder & Instructor, Research Spectrum'

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: MeCertificatesResponse }

function toFixture(item: MeCertificatesResponse['certificates'][number]): CertificateFixture {
  return {
    studentName: item.studentName,
    courseTitle: item.courseTitle,
    credentialId: item.credentialId,
    issueLabel: item.issueDate,
    instructorName: item.instructorName || DEFAULT_INSTRUCTOR_NAME,
    instructorTitle: item.instructorTitle || DEFAULT_INSTRUCTOR_TITLE,
    status: item.status,
    verifyPath: `/verify/${item.credentialId}`,
  }
}

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load certificates'
}

async function downloadCertificate(certificate: CertificateFixture): Promise<void> {
  const { generateCertificatePDF } = await import('./certificates/certificatePdf')
  generateCertificatePDF({
    name: certificate.studentName,
    title: certificate.courseTitle,
    cred: certificate.credentialId,
    date: certificate.issueLabel,
  })
}

async function copyShareLink(verifyPath: string): Promise<void> {
  const url = `${window.location.origin}${verifyPath}`
  await navigator.clipboard.writeText(url)
}

export default function CertificatesPage() {
  usePageTitle('Certificates')

  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [fetchKey, setFetchKey] = useState(0)

  const retry = useCallback(() => {
    setState({ status: 'loading' })
    setFetchKey((key) => key + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      setState({ status: 'loading' })
      try {
        const data = await listMyCertificates()
        if (cancelled) return
        setState({ status: 'ready', data })
      } catch (err) {
        if (cancelled) return
        setState({ status: 'error', message: errorMessage(err) })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [fetchKey])

  const ready = state.status === 'ready' ? state.data : null
  const isEmpty =
    ready !== null &&
    ready.certificates.length === 0 &&
    ready.inProgress.length === 0 &&
    ready.profileIncomplete.length === 0

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-certificates">
      <section className="border-b border-rs-line bg-rs-sky-2 px-5 py-12 sm:px-7 sm:py-16">
        <div className="mx-auto max-w-wrap text-center">
          <p className="mb-3 text-[13px] font-bold uppercase tracking-[0.12em] text-rs-blue">
            Credentials
          </p>
          <h1 className="text-[clamp(28px,4vw,42px)] font-extrabold tracking-tight text-rs-ink">
            Your Certificates
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-[16px] leading-relaxed text-rs-body">
            Download, share, and verify competency-based certificates earned across Research Spectrum
            courses.
          </p>
        </div>
      </section>

      <section className="px-5 py-10 sm:px-7 sm:py-12">
        <div className="mx-auto max-w-wrap space-y-10">
          {state.status === 'loading' ? (
            <p className="text-center text-rs-body">Loading your certificates…</p>
          ) : null}

          {state.status === 'error' ? (
            <div className="mx-auto flex max-w-lg flex-col items-center gap-4 text-center">
              <p className="text-rs-body">{state.message}</p>
              <Button type="button" variant="ghost" onClick={retry}>
                Try again
              </Button>
            </div>
          ) : null}

          {ready && isEmpty ? (
            <p className="text-center text-rs-body">
              No certificates yet. Complete a course to earn your first credential.
            </p>
          ) : null}

          {ready && ready.certificates.length > 0 ? (
            <div>
              <h2 className="mb-5 text-xl font-extrabold text-rs-ink">Earned</h2>
              <div className="grid gap-6 sm:grid-cols-2">
                {ready.certificates.map((item) => {
                  const certificate = toFixture(item)
                  return (
                    <CertificateCard
                      key={item.id}
                      certificate={certificate}
                      onDownload={() => {
                        void downloadCertificate(certificate)
                      }}
                      onCopyShareLink={() => {
                        void copyShareLink(certificate.verifyPath)
                      }}
                    />
                  )
                })}
              </div>
            </div>
          ) : null}

          {ready && (ready.inProgress.length > 0 || ready.profileIncomplete.length > 0) ? (
            <div>
              <h2 className="mb-5 text-xl font-extrabold text-rs-ink">In progress</h2>
              <div className="grid gap-6 sm:grid-cols-2">
                {ready.profileIncomplete
                  .filter((item) => item.requirementsMet)
                  .map((item) => (
                    <CertificateProgressCard
                      key={`incomplete-${item.courseId}`}
                      incomplete={{
                        courseTitle: item.courseTitle,
                        requirementsMet: true,
                        message: item.message,
                        href: item.href,
                      }}
                    />
                  ))}
                {ready.inProgress.map((item) => (
                  <CertificateProgressCard
                    key={`progress-${item.courseId}`}
                    progress={{
                      courseTitle: item.courseTitle,
                      passedCount: item.passedCount,
                      totalCount: item.totalCount,
                    }}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}
