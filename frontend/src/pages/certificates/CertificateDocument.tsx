import brandMark from '../../assets/brand/research-spectrum-mark.webp'
import certificateWash from './certificate-wash.png'
import type { CertificateFixture } from './certificateFixture'
import { durationLine } from './courseCertificateMeta'
import './CertificateDocument.css'

type CertificateDocumentProps = {
  certificate: CertificateFixture
  qrSrc?: string
}

function publicVerifyUrl(credentialId: string): string {
  return `https://researchspectrum.org/verify/${credentialId}`
}

/** Printable course certificate layout (landscape 1123×794). */
export function CertificateDocument({ certificate, qrSrc }: CertificateDocumentProps) {
  const hoursLine = durationLine(certificate.courseTitle)
  const verifyUrl = publicVerifyUrl(certificate.credentialId)

  return (
    <article className="certificate-document" data-testid="certificate-document">
      <img
        className="certificate-document__layer certificate-document__glow"
        src={certificateWash}
        alt=""
        aria-hidden="true"
      />
      <img
        className="certificate-document__layer certificate-document__wm"
        src={brandMark}
        alt=""
        aria-hidden="true"
      />

      <svg
        className="certificate-document__layer certificate-document__frame"
        viewBox="0 0 1123 794"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="cert-doc-gb" x1="0" x2="1">
            <stop offset="0" stopColor="#0a1733" />
            <stop offset="1" stopColor="#1e5eff" />
          </linearGradient>
          <g id="cert-doc-cn">
            <path d="M30 30H118V37H37V118H30Z" fill="url(#cert-doc-gb)" />
            <path d="M52 44l8 8-8 8-8-8z" fill="#b8923a" />
            <circle cx="76" cy="40" r="2.5" fill="#b8923a" />
            <circle cx="40" cy="76" r="2.5" fill="#b8923a" />
          </g>
        </defs>
        <rect x="14" y="14" width="1095" height="766" stroke="url(#cert-doc-gb)" strokeWidth="3" />
        <rect x="22" y="22" width="1079" height="750" stroke="#b8923a" strokeWidth="1" />
        <rect x="30" y="30" width="1063" height="734" stroke="#dfe6f5" strokeWidth="1" />
        <use href="#cert-doc-cn" />
        <use href="#cert-doc-cn" transform="translate(1123 0) scale(-1 1)" />
        <use href="#cert-doc-cn" transform="translate(0 794) scale(1 -1)" />
        <use href="#cert-doc-cn" transform="translate(1123 794) scale(-1 -1)" />
      </svg>

      <div className="certificate-document__layer certificate-document__head">
        <div className="certificate-document__brand">
          <img src={brandMark} alt="" />
          <div className="certificate-document__brand-name">
            Research <span>Spectrum</span>
          </div>
        </div>
        <div className="certificate-document__tag">Evidence-Based Research Education</div>
      </div>

      <div className="certificate-document__layer certificate-document__t1">CERTIFICATE</div>
      <div className="certificate-document__layer certificate-document__t2">OF COMPLETION</div>
      <p className="certificate-document__layer certificate-document__pre">
        This certificate is proudly presented to
      </p>
      <p className="certificate-document__layer certificate-document__name certificate-document__student">
        {certificate.studentName}
      </p>
      <div className="certificate-document__layer certificate-document__rule" aria-hidden="true" />

      <div className="certificate-document__layer certificate-document__mid">
        <p>for successfully completing the course</p>
        <h2 className="certificate-document__course">{certificate.courseTitle}</h2>
        {hoursLine ? <small className="certificate-document__hours">{hoursLine}</small> : null}
      </div>

      <div className="certificate-document__layer certificate-document__foot">
        <div className="certificate-document__sig">
          <div className="certificate-document__sig-script">Bahaa Aburayya</div>
          <div className="certificate-document__sig-line">
            <b>Dr. Bahaa Aburayya, MD</b>
            <span>Founder &amp; Course Instructor</span>
          </div>
        </div>

        <div className="certificate-document__seal">
        <svg viewBox="0 0 140 156" aria-hidden="true">
          <defs>
            <linearGradient id="cert-doc-gg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#f4df9c" />
              <stop offset="0.5" stopColor="#c9a24d" />
              <stop offset="1" stopColor="#8f6b1f" />
            </linearGradient>
            <linearGradient id="cert-doc-rb" x1="0" x2="1">
              <stop offset="0" stopColor="#0a1733" />
              <stop offset="1" stopColor="#1e5eff" />
            </linearGradient>
          </defs>
          <polygon points="40,90 66,98 54,150 40,134 24,144" fill="url(#cert-doc-rb)" />
          <polygon points="100,90 74,98 86,150 100,134 116,144" fill="url(#cert-doc-rb)" />
          <circle cx="70" cy="70" r="66" fill="url(#cert-doc-gg)" />
          <circle
            cx="70"
            cy="70"
            r="62"
            fill="none"
            stroke="#fff"
            strokeOpacity="0.55"
            strokeWidth="3"
            strokeDasharray="2 5"
            strokeLinecap="round"
          />
          <circle cx="70" cy="70" r="50" fill="#fff" />
          <circle cx="70" cy="70" r="46" fill="none" stroke="#b8923a" strokeWidth="1.5" />
          <text
            x="70"
            y="108"
            textAnchor="middle"
            fontFamily="Plus Jakarta Sans, sans-serif"
            fontSize="7.5"
            fontWeight="800"
            letterSpacing="2"
            fill="#0a1733"
          >
            VERIFIED
          </text>
        </svg>
        <img className="certificate-document__seal-logo" src={brandMark} alt="" />
        </div>

        <div className="certificate-document__ver">
          <div className="certificate-document__meta">
            <b className="certificate-document__issued">{certificate.issueLabel}</b>
            <span>Date of Issue</span>
            <code className="certificate-document__credential">{certificate.credentialId}</code>
            <span>Credential ID</span>
          </div>
          <div className="certificate-document__qr" data-verify-url={verifyUrl}>
            {qrSrc ? <img src={qrSrc} alt="" /> : null}
          </div>
        </div>
      </div>
    </article>
  )
}
