import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import {
  getPublicCertificate,
  type PublicCertificateResult,
} from '../lib/api/public-certificates'
import { usePageTitle } from '../lib/page-title'
import { CertificateVerifyDocument } from './certificates/CertificateVerifyDocument'
import type { CertificateFixture } from './certificates/certificateFixture'

const DEFAULT_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'
const DEFAULT_INSTRUCTOR_TITLE = 'Founder & Instructor, Research Spectrum'

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; result: PublicCertificateResult }

function toFixture(result: Extract<PublicCertificateResult, { status: 'valid' | 'revoked' }>): CertificateFixture {
  return {
    studentName: result.studentName,
    courseTitle: result.courseTitle,
    credentialId: result.credentialId,
    issueLabel: result.issueDate,
    instructorName: result.instructorName || DEFAULT_INSTRUCTOR_NAME,
    instructorTitle: result.instructorTitle || DEFAULT_INSTRUCTOR_TITLE,
    status: result.status,
    verifyPath: `/verify/${result.credentialId}`,
  }
}

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to verify certificate'
}

export default function VerifyCertificatePage() {
  usePageTitle('Verify Certificate')
  const { credentialId: routeCredentialId } = useParams<{ credentialId?: string }>()
  const navigate = useNavigate()
  const [inputValue, setInputValue] = useState(routeCredentialId ?? '')
  const [state, setState] = useState<LoadState>(
    routeCredentialId ? { status: 'loading' } : { status: 'idle' },
  )

  const lookup = useCallback(async (credentialId: string) => {
    const trimmed = credentialId.trim()
    if (!trimmed) {
      setState({ status: 'idle' })
      return
    }
    setState({ status: 'loading' })
    try {
      const result = await getPublicCertificate(trimmed)
      setState({ status: 'ready', result })
    } catch (err) {
      setState({ status: 'error', message: errorMessage(err) })
    }
  }, [])

  useEffect(() => {
    setInputValue(routeCredentialId ?? '')
    if (routeCredentialId) {
      void lookup(routeCredentialId)
    } else {
      setState({ status: 'idle' })
    }
  }, [routeCredentialId, lookup])

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = inputValue.trim()
    if (!trimmed) return
    if (trimmed === routeCredentialId) {
      void lookup(trimmed)
      return
    }
    void navigate(`/verify/${encodeURIComponent(trimmed)}`)
  }

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-verify-certificate">
      <section className="border-b border-rs-line bg-rs-sky-2 px-5 py-12 sm:px-7 sm:py-16">
        <div className="mx-auto max-w-wrap text-center">
          <p className="mb-3 text-[13px] font-bold uppercase tracking-[0.12em] text-rs-blue">
            Public verification
          </p>
          <h1 className="text-[clamp(28px,4vw,42px)] font-extrabold tracking-tight text-rs-ink">
            Verify Certificate Authenticity
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-[16px] leading-relaxed text-rs-body">
            Instantly verify the status and validity of Research Spectrum certificates using a unique
            credential ID.
          </p>
        </div>
      </section>

      <section className="px-5 py-10 sm:px-7 sm:py-12">
        <div className="mx-auto max-w-2xl space-y-8">
          <form
            onSubmit={onSubmit}
            className="rounded-[22px] border border-rs-line bg-white p-6 shadow-rs-lg sm:p-8"
          >
            <label htmlFor="credential-id" className="mb-2 block text-sm font-bold text-rs-navy">
              Credential ID
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                id="credential-id"
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                placeholder="e.g. RS-A1B7F3-2026-9C2E10B4D8"
                className="min-w-0 flex-1 rounded-[14px] border-[1.5px] border-rs-line px-[18px] py-3 text-[15.5px] text-rs-ink outline-none focus:border-rs-blue focus:shadow-[0_0_0_3px_rgba(30,94,255,.10)]"
              />
              <Button type="submit" variant="primary" className="justify-center whitespace-nowrap">
                Verify Certificate
              </Button>
            </div>
          </form>

          {state.status === 'loading' ? (
            <p className="text-center text-rs-body">Looking up certificate…</p>
          ) : null}

          {state.status === 'error' ? (
            <p className="text-center text-rs-body">{state.message}</p>
          ) : null}

          {state.status === 'ready' && state.result.status === 'not_found' ? (
            <CertificateVerifyDocument result={state.result} />
          ) : null}

          {state.status === 'ready' && state.result.status !== 'not_found' ? (
            <CertificateVerifyDocument certificate={toFixture(state.result)} />
          ) : null}
        </div>
      </section>
    </div>
  )
}
