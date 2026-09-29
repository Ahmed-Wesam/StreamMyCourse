import { Check, Shield } from 'lucide-react'
import type { CertificateFixture, CertificateNotFoundFixture } from './certificateFixture'

type CertificateVerifyDocumentProps =
  | { certificate: CertificateFixture; result?: undefined }
  | { result: CertificateNotFoundFixture; certificate?: undefined }

function statusPill(status: 'valid' | 'revoked' | 'not_found') {
  if (status === 'valid') {
    return {
      label: 'Verified',
      className: 'border border-[#bce7c8] bg-[#dcf5e3] text-[#0d6f3e]',
    }
  }
  if (status === 'revoked') {
    return {
      label: 'Revoked',
      className: 'border border-[#fecaca] bg-[#fee2e2] text-[#b91c1c]',
    }
  }
  return {
    label: 'Not Found',
    className: 'border border-rs-line-2 bg-[#f1f4fb] text-rs-muted',
  }
}

export function CertificateVerifyDocument(props: CertificateVerifyDocumentProps) {
  if (props.result?.status === 'not_found') {
    const pill = statusPill('not_found')
    return (
      <div className="rounded-2xl border border-rs-line border-t-4 border-t-rs-line bg-white p-8 shadow-rs-sm">
        <span
          className={`mb-5 inline-flex items-center gap-2 rounded-full px-[18px] py-2 text-[13px] font-extrabold uppercase tracking-wider ${pill.className}`}
        >
          {pill.label}
        </span>
        <h3 className="text-xl font-extrabold tracking-tight text-rs-ink">Certificate Not Found</h3>
        <p className="mt-2 text-[15px] leading-relaxed text-rs-body">
          No certificate matching this credential ID was found in the Research Spectrum system.
        </p>
      </div>
    )
  }

  const certificate = props.certificate
  if (!certificate) {
    return null
  }

  const isRevoked = certificate.status === 'revoked'
  const pill = statusPill(certificate.status)
  const statusLabel = isRevoked ? 'Revoked' : 'Verified'
  const statusColor = isRevoked ? 'text-[#b91c1c]' : 'text-[#0d6f3e]'

  return (
    <div className="overflow-hidden rounded-2xl border-2 border-rs-line bg-white shadow-rs">
      <div className="relative overflow-hidden bg-rs-grad px-9 pb-6 pt-7">
        <div className="relative z-[1]">
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-lg font-extrabold tracking-tight text-white">
              <div className="flex size-[34px] items-center justify-center rounded-[10px] bg-white/18">
                <Shield className="size-5 text-white" aria-hidden />
              </div>
              Research Spectrum
            </div>
            <span
              className={`rounded-full border px-3.5 py-1 text-xs font-extrabold uppercase tracking-wider ${pill.className}`}
            >
              {pill.label}
            </span>
          </div>
          <p className="mb-1.5 text-xs font-extrabold uppercase tracking-[0.14em] text-white/75">
            Certificate of Completion
          </p>
          <h2 className="mb-1.5 text-[clamp(18px,3vw,26px)] font-extrabold leading-tight tracking-tight text-white">
            {certificate.courseTitle}
          </h2>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/24 bg-white/16 px-3.5 py-1 text-[13px] font-bold text-white/92">
            <Check className="size-[13px]" aria-hidden strokeWidth={2} />
            {certificate.courseTitle}
          </span>
        </div>
      </div>

      <div className="bg-white px-9 pb-6 pt-7">
        <p className="mb-1.5 text-[11.5px] font-extrabold uppercase tracking-[0.1em] text-rs-muted">
          This certifies that
        </p>
        <p className="mb-5 text-[clamp(24px,4vw,36px)] font-extrabold leading-none tracking-tight text-rs-ink">
          {certificate.studentName}
        </p>

        <div className="mb-[22px] grid gap-3.5 sm:grid-cols-3">
          <div className="rounded-xl border border-rs-line-2 bg-rs-sky-2 px-3.5 py-3">
            <p className="mb-0.5 text-[10.5px] font-extrabold uppercase tracking-wider text-rs-muted">
              Credential ID
            </p>
            <p className="text-xs font-extrabold tracking-tight text-rs-ink">{certificate.credentialId}</p>
          </div>
          <div className="rounded-xl border border-rs-line-2 bg-rs-sky-2 px-3.5 py-3">
            <p className="mb-0.5 text-[10.5px] font-extrabold uppercase tracking-wider text-rs-muted">
              Issue Date
            </p>
            <p className="text-[13.5px] font-extrabold tracking-tight text-rs-ink">{certificate.issueLabel}</p>
          </div>
          <div className="rounded-xl border border-rs-line-2 bg-rs-sky-2 px-3.5 py-3">
            <p className="mb-0.5 text-[10.5px] font-extrabold uppercase tracking-wider text-rs-muted">Status</p>
            <p className={`text-[13.5px] font-extrabold tracking-tight ${statusColor}`}>{statusLabel}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-4 border-t border-rs-line-2 pt-[18px]">
          <div>
            <div className="mb-1.5 h-[1.5px] w-40 bg-rs-line" />
            <p className="mb-px text-[13px] font-extrabold text-rs-ink">{certificate.instructorName}</p>
            <p className="text-[11.5px] font-semibold text-rs-muted">{certificate.instructorTitle}</p>
          </div>
          <div className="flex size-[72px] shrink-0 items-center justify-center rounded-full bg-rs-grad-cta text-white shadow-[0_8px_24px_-8px_rgba(30,94,255,.55)]">
            <Shield className="size-9" aria-hidden strokeWidth={2.2} />
          </div>
        </div>

        <p className="mt-3.5 border-t border-rs-line-2 pt-3.5 text-center font-mono text-[11px] font-bold tracking-wider text-rs-muted">
          Credential ID: {certificate.credentialId} · Issued by Research Spectrum · {certificate.verifyPath}
        </p>
      </div>
    </div>
  )
}
