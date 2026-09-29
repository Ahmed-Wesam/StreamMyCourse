import { Check, Download, Link2, ShieldCheck } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import type { CertificateFixture } from './certificateFixture'

type CertificateCardProps = {
  certificate: CertificateFixture
  onDownload?: () => void
  onCopyShareLink?: () => void
}

function SealIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className="size-8" aria-hidden>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
    </svg>
  )
}

export function CertificateCard({ certificate, onDownload, onCopyShareLink }: CertificateCardProps) {
  const isRevoked = certificate.status === 'revoked'

  return (
    <article className="relative overflow-hidden rounded-[22px] border-2 border-rs-line bg-gradient-to-b from-white to-[#fafcff] px-8 pb-[30px] pt-10 text-center shadow-rs-lg">
      <div className="pointer-events-none absolute inset-2.5 rounded-[14px] border border-[#dce8ff]" aria-hidden />

      <div className="relative z-[1]">
        <div className="mx-auto mb-[18px] flex size-[72px] items-center justify-center rounded-full bg-rs-grad-cta text-white shadow-[0_14px_30px_-8px_rgba(30,94,255,.55)]">
          <SealIcon />
        </div>

        <p className="mb-2 text-[10.5px] font-extrabold uppercase tracking-[0.2em] text-rs-muted">
          Certificate of Completion
        </p>
        <h3 className="mb-1 bg-rs-grad bg-clip-text text-2xl font-extrabold leading-[1.15] tracking-tight text-transparent">
          {certificate.courseTitle}
        </h3>
        <p className="text-[12.5px] font-semibold text-rs-muted">Research Spectrum</p>

        <p className="mb-[5px] mt-5 text-[11px] font-bold uppercase tracking-[0.1em] text-rs-muted">
          Awarded To
        </p>
        <p className="text-xl font-extrabold leading-tight tracking-tight text-rs-navy">
          {certificate.studentName}
        </p>

        <div className="my-4 flex justify-center gap-7 border-y border-rs-line-2 py-3.5">
          <div className="text-center">
            <p className="mb-1 text-[10.5px] font-bold uppercase tracking-wider text-rs-muted">Issued</p>
            <p className="text-[13px] font-extrabold tracking-tight text-rs-navy">{certificate.issueLabel}</p>
          </div>
          <div className="text-center">
            <p className="mb-1 text-[10.5px] font-bold uppercase tracking-wider text-rs-muted">Credential ID</p>
            <p className="text-[13px] font-extrabold tracking-tight text-rs-navy">{certificate.credentialId}</p>
          </div>
        </div>

        {isRevoked ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[#fecaca] bg-[#fee2e2] px-3.5 py-1.5 text-xs font-bold text-[#b91c1c]">
            Revoked
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[#bce7c8] bg-[#dcf5e3] px-3.5 py-1.5 text-xs font-bold text-[#0d6f3e]">
            <Check className="size-3" aria-hidden strokeWidth={2.6} />
            Verified
          </span>
        )}

        <div className="mt-4 flex items-start justify-between border-t border-rs-line pt-3.5">
          <div className="text-left">
            <b className="mt-5 block border-t-[1.5px] border-rs-navy pt-2 text-[12.5px] font-extrabold tracking-tight text-rs-navy">
              Research Spectrum
            </b>
            <span className="mt-0.5 block text-[11px] font-semibold text-rs-muted">Issuing Platform</span>
          </div>
          <div className="text-right">
            <b className="mt-5 block border-t-[1.5px] border-rs-navy pt-2 text-[12.5px] font-extrabold tracking-tight text-rs-navy">
              {certificate.issueLabel}
            </b>
            <span className="mt-0.5 block text-[11px] font-semibold text-rs-muted">Issue Date</span>
          </div>
        </div>

        <div className="mt-[22px] border-t border-rs-line pt-[22px]">
          <div className="flex flex-col gap-2.5">
            <Button
              type="button"
              variant="primary"
              disabled={!onDownload || isRevoked}
              className="w-full justify-center text-[14.5px]"
              onClick={onDownload}
            >
              <Download className="size-[17px]" aria-hidden />
              Download Certificate
            </Button>
            <Button
              href={certificate.verifyPath}
              variant="ghost"
              className="w-full justify-center text-[14.5px]"
            >
              <ShieldCheck className="size-[17px]" aria-hidden />
              Verify Certificate
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={!onCopyShareLink}
              className="w-full justify-center text-[14.5px]"
              onClick={onCopyShareLink}
            >
              <Link2 className="size-[17px]" aria-hidden />
              Copy Share Link
            </Button>
          </div>
        </div>
      </div>
    </article>
  )
}
