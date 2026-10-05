import { useState } from 'react'
import { Link } from 'react-router-dom'

import type { CertificateFixture } from './certificateFixture'
import { sealKeyForTitle } from './courseCertificateMeta'
import { CourseSealIcon } from './CourseSealIcon'

type CertificateCardProps = {
  certificate: CertificateFixture
  onDownload?: () => void
  onCopyShareLink?: () => void | Promise<void>
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  )
}

export function CertificateCard({ certificate, onDownload, onCopyShareLink }: CertificateCardProps) {
  const isRevoked = certificate.status === 'revoked'
  const [copied, setCopied] = useState(false)
  const sealKey = sealKeyForTitle(certificate.courseTitle)

  async function handleCopyShareLink() {
    if (!onCopyShareLink) return
    await onCopyShareLink()
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2200)
  }

  return (
    <article className="cert-full reveal">
      <CourseSealIcon sealKey={sealKey} variant="earned" />
      <p className="cf-eyebrow">Certificate of Completion</p>
      <h3 className="cf-title">{certificate.courseTitle}</h3>
      <p className="cf-platform">Research Spectrum</p>
      <p className="cf-awarded-lbl">Awarded To</p>
      <p className="cf-student-name">{certificate.studentName}</p>
      <div className="cf-meta-row">
        <div className="cf-meta-col">
          <p className="cf-meta-lbl">Issued</p>
          <p className="cf-meta-val">{certificate.issueLabel}</p>
        </div>
        <div className="cf-meta-col">
          <p className="cf-meta-lbl">Credential ID</p>
          <p className="cf-meta-val">{certificate.credentialId}</p>
        </div>
      </div>
      <span className={isRevoked ? 'cf-verified revoked' : 'cf-verified'}>
        {isRevoked ? null : <CheckIcon />}
        {isRevoked ? 'Revoked' : 'Verified Certificate'}
      </span>
      <div className="cf-sig">
        <div className="cf-sig-col">
          <b>Research Spectrum</b>
          <span>Issuing Platform</span>
        </div>
        <div className="cf-sig-col right">
          <b>{certificate.issueLabel}</b>
          <span>Issue Date</span>
        </div>
      </div>
      <div className="cf-divider" />
      <div className="cf-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!onDownload || isRevoked}
          onClick={onDownload}
        >
          <DownloadIcon />
          Download Certificate
        </button>
        <Link to={certificate.verifyPath} className="btn btn-ghost">
          <CheckIcon />
          Verify Certificate
        </Link>
        <button
          type="button"
          className={copied ? 'btn btn-ghost copied' : 'btn btn-ghost'}
          disabled={!onCopyShareLink || isRevoked}
          onClick={() => {
            void handleCopyShareLink()
          }}
        >
          {copied ? (
            <>
              <CheckIcon />
              Link Copied!
            </>
          ) : (
            <>
              <LinkIcon />
              Copy Share Link
            </>
          )}
        </button>
      </div>
    </article>
  )
}
