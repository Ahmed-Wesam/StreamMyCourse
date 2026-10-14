import brandMark from '../../assets/brand/research-spectrum-mark.webp'
import type { BundleCertificateFixture } from './certificateFixture'
import { bundlePathwayRows, bundleTotalHours } from './courseCertificateMeta'
import './BundleCertificateDocument.css'

type BundleCertificateDocumentProps = {
  certificate: BundleCertificateFixture
}

const BUNDLE_TITLE = 'Research Mastery Bundle'
const HOURS_ASSESSMENT_SUFFIX = ' · Competency-Based Assessment'

function publicVerifyUrl(credentialId: string): string {
  return `https://researchspectrum.org/verify/${credentialId}`
}

/** Printable bundle certificate layout (landscape 1123×794). */
export function BundleCertificateDocument({ certificate }: BundleCertificateDocumentProps) {
  const pathwayRows = bundlePathwayRows()
  const totalHours = bundleTotalHours()
  const verifyUrl = publicVerifyUrl(certificate.credentialId)
  const bundleHoursLine = `${totalHours} Hours${HOURS_ASSESSMENT_SUFFIX}`

  return (
    <article className="bundle-certificate-document" data-testid="bundle-certificate-document">
      <div className="bundle-certificate-document__layer bundle-certificate-document__glow" aria-hidden="true" />
      <img
        className="bundle-certificate-document__layer bundle-certificate-document__wm"
        src={brandMark}
        alt=""
        aria-hidden="true"
      />

      <aside className="bundle-certificate-document__layer bundle-certificate-document__side">
        <div className="bundle-certificate-document__layer bundle-certificate-document__edge" aria-hidden="true" />
        <div className="bundle-certificate-document__layer bundle-certificate-document__badge">
          <img src={brandMark} alt="" />
        </div>
        <div className="bundle-certificate-document__layer bundle-certificate-document__path-tag">
          The Complete Path
        </div>
        <div className="bundle-certificate-document__layer bundle-certificate-document__path-sub">
          Four courses · One program
        </div>
        <div className="bundle-certificate-document__layer bundle-certificate-document__items">
          {pathwayRows.map((row, index) => (
            <div key={row.title} className="bundle-certificate-document__item">
              <div className="bundle-certificate-document__item-n">{index + 1}</div>
              <div className="bundle-certificate-document__item-t">{row.title}</div>
              <div className="bundle-certificate-document__item-h">{row.hours} Hours</div>
            </div>
          ))}
        </div>
        <div className="bundle-certificate-document__layer bundle-certificate-document__total">
          <b>{totalHours}</b>
          <span>Total Hours</span>
        </div>
      </aside>

      <svg
        className="bundle-certificate-document__layer bundle-certificate-document__frame"
        viewBox="0 0 1123 794"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="bundle-cert-gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#f4df9c" />
            <stop offset="0.5" stopColor="#c9a24d" />
            <stop offset="1" stopColor="#8f6b1f" />
          </linearGradient>
          <g id="bundle-cert-cn">
            <path d="M0 0H88V7H7V88H0Z" fill="url(#bundle-cert-gold)" />
            <path d="M22 14l8 8-8 8-8-8z" fill="#0a1733" />
            <circle cx="46" cy="10" r="2.5" fill="#b8923a" />
            <circle cx="10" cy="46" r="2.5" fill="#b8923a" />
          </g>
        </defs>
        <rect x="14" y="14" width="1095" height="766" stroke="url(#bundle-cert-gold)" strokeWidth="3" />
        <rect x="22" y="22" width="1079" height="750" stroke="#b8923a" strokeWidth="1" strokeOpacity="0.7" />
        <use href="#bundle-cert-cn" transform="translate(1093 30) scale(-1 1)" />
        <use href="#bundle-cert-cn" transform="translate(1093 764) scale(-1 -1)" />
        <use href="#bundle-cert-cn" transform="translate(312 764) scale(1 -1)" />
        <use href="#bundle-cert-cn" transform="translate(312 30)" />
      </svg>

      <header className="bundle-certificate-document__layer bundle-certificate-document__head">
        <div className="bundle-certificate-document__tag">Research Spectrum</div>
        <div className="bundle-certificate-document__tag">Evidence-Based Research Education</div>
      </header>

      <div className="bundle-certificate-document__layer bundle-certificate-document__t1">CERTIFICATE</div>
      <div className="bundle-certificate-document__layer bundle-certificate-document__t2">OF MASTERY</div>
      <p className="bundle-certificate-document__layer bundle-certificate-document__pre">
        This certificate is proudly presented to
      </p>
      <p className="bundle-certificate-document__layer bundle-certificate-document__name">
        {certificate.studentName}
      </p>
      <div className="bundle-certificate-document__layer bundle-certificate-document__rule" aria-hidden="true" />

      <div className="bundle-certificate-document__layer bundle-certificate-document__mid">
        <p>for successfully completing all four courses of the</p>
        <h2 className="bundle-certificate-document__program">{BUNDLE_TITLE}</h2>
        <small className="bundle-certificate-document__hours">{bundleHoursLine}</small>
      </div>

      <footer className="bundle-certificate-document__layer bundle-certificate-document__foot">
        <div className="bundle-certificate-document__sig">
          <div className="bundle-certificate-document__sig-script">Bahaa Aburayya</div>
          <div className="bundle-certificate-document__sig-line">
            <b>{certificate.instructorName}</b>
            <span>{certificate.instructorTitle}</span>
          </div>
        </div>

        <svg className="bundle-certificate-document__seal" viewBox="0 0 140 160" aria-hidden="true">
          <defs>
            <linearGradient id="bundle-cert-gg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#f4df9c" />
              <stop offset="0.5" stopColor="#c9a24d" />
              <stop offset="1" stopColor="#8f6b1f" />
            </linearGradient>
            <linearGradient id="bundle-cert-rb" x1="0" x2="1">
              <stop offset="0" stopColor="#0a1733" />
              <stop offset="1" stopColor="#1e5eff" />
            </linearGradient>
          </defs>
          <polygon points="46,96 70,104 60,152 46,140 32,152" fill="url(#bundle-cert-rb)" />
          <polygon points="94,96 70,104 80,152 94,140 108,152" fill="url(#bundle-cert-rb)" />
          <polygon
            points="70.0,4.0 78.1,8.5 87.1,6.2 93.7,12.7 103.0,12.8 107.7,20.8 116.7,23.3 119.2,32.3 127.2,37.0 127.3,46.3 133.8,52.9 131.5,61.9 136.0,70.0 131.5,78.1 133.8,87.1 127.3,93.7 127.2,103.0 119.2,107.7 116.7,116.7 107.7,119.2 103.0,127.2 93.7,127.3 87.1,133.8 78.1,131.5 70.0,136.0 61.9,131.5 52.9,133.8 46.3,127.3 37.0,127.2 32.3,119.2 23.3,116.7 20.8,107.7 12.8,103.0 12.7,93.7 6.2,87.1 8.5,78.1 4.0,70.0 8.5,61.9 6.2,52.9 12.7,46.3 12.8,37.0 20.8,32.3 23.3,23.3 32.3,20.8 37.0,12.8 46.3,12.7 52.9,6.2 61.9,8.5"
            fill="url(#bundle-cert-gg)"
          />
          <circle cx="70" cy="70" r="55" fill="#0a1733" />
          <circle cx="70" cy="70" r="50" fill="none" stroke="#e6c871" strokeWidth="1.2" />
          <circle cx="70" cy="62" r="30" fill="#fff" />
          <image href={brandMark} x="51" y="46" width="38" height="33" preserveAspectRatio="xMidYMid meet" />
          <text
            x="70"
            y="108"
            textAnchor="middle"
            fontFamily="Plus Jakarta Sans, sans-serif"
            fontSize="8"
            fontWeight="800"
            letterSpacing="2.2"
            fill="#e6c871"
          >
            MASTERY
          </text>
        </svg>

        <div className="bundle-certificate-document__ver">
          <div className="bundle-certificate-document__meta">
            <b>{certificate.issueLabel}</b>
            <span>Date of Issue</span>
            <code>{certificate.credentialId}</code>
            <span>Credential ID</span>
            <em>{verifyUrl}</em>
          </div>
        </div>
      </footer>
    </article>
  )
}
