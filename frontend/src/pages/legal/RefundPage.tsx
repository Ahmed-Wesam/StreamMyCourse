import { useRef } from 'react'
import { Link } from 'react-router-dom'

import { usePageTitle } from '../../lib/page-title'
import { usePolicySidebar } from './usePolicySidebar'
import './RefundPage.css'

export default function RefundPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  usePageTitle("Refund & Cancellation Policy")
  usePolicySidebar(rootRef)

  return (
    <div ref={rootRef} className="pg-refund text-rs-ink">
      <section className="pp-hero">
        <div className="wrap">
          <div className="eyebrow"><span className="dot" />Refund &amp; Cancellation Policy</div>
          <h1 style={{ marginTop: "16px" }} aria-label="Research Spectrum Refund & Cancellation Policy">Research Spectrum Refund<br />&amp; Cancellation Policy</h1>
          <p className="sub">
            Review the policies governing refunds, cancellations, digital product purchases, chargebacks, and exceptional circumstances relating to Research Spectrum services.
          </p>
          <div className="pp-meta">
            <span className="pp-meta-pill">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              Last Updated: June 2026
            </span>
            <span className="pp-meta-pill">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              Hashemite Kingdom of Jordan
            </span>
            <span className="pp-meta-pill">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              </svg>
              Digital Products
            </span>
          </div>
          <div className="legal-notice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>
              This Refund &amp; Cancellation Policy governs purchases made through Research Spectrum and should be reviewed periodically for updates. Continued use of Research Spectrum Services following publication of updated policies constitutes acceptance of the revised policy.
            </p>
          </div>
        </div>
      </section>
      {/* POLICY LAYOUT */}
      <div className="policy-layout">
        {/* SIDEBAR */}
        <aside className="policy-sidebar">
          <div className="sidebar-card">
            <div className="sidebar-title">Contents</div>
            <nav className="sidebar-nav" id="sidebarNav" aria-label="Policy sections">
              <button className="sidebar-link" data-target="rp-intro" type="button"><span className="sl-num">—</span>Introduction</button>
              <button className="sidebar-link" data-target="rp-1" type="button"><span className="sl-num">1.</span>Digital Product Nature</button>
              <button className="sidebar-link" data-target="rp-2" type="button"><span className="sl-num">2.</span>No Refund Policy</button>
              <button className="sidebar-link" data-target="rp-3" type="button"><span className="sl-num">3.</span>Course Access After Purchase</button>
              <button className="sidebar-link" data-target="rp-4" type="button"><span className="sl-num">4.</span>Fraudulent Purchases</button>
              <button className="sidebar-link" data-target="rp-5" type="button"><span className="sl-num">5.</span>Chargebacks &amp; Disputes</button>
              <button className="sidebar-link" data-target="rp-6" type="button"><span className="sl-num">6.</span>Cancellation of Services</button>
              <button className="sidebar-link" data-target="rp-7" type="button"><span className="sl-num">7.</span>Future Services</button>
              <button className="sidebar-link" data-target="rp-8" type="button"><span className="sl-num">8.</span>Exceptional Circumstances</button>
              <button className="sidebar-link" data-target="rp-9" type="button"><span className="sl-num">9.</span>Policy Changes</button>
              <button className="sidebar-link" data-target="rp-10" type="button"><span className="sl-num">10.</span>Language</button>
              <button className="sidebar-link" data-target="rp-11" type="button"><span className="sl-num">11.</span>Contact</button>
            </nav>
          </div>
        </aside>
        {/* CONTENT */}
        <div className="policy-main">
          <div className="policy-content">
            {/* Introduction */}
            <div className="policy-intro-section" id="rp-intro">
              <div className="pi-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="1" y="4" width="22" height="16" rx="2" />
                  <line x1="1" y1="10" x2="23" y2="10" />
                </svg>
                Refund &amp; Cancellation Policy
              </div>
              <div className="ps-body">
                <p>
                  Research Spectrum is committed to providing high-quality educational content and learning experiences. Because our products consist primarily of digital educational content that is delivered immediately upon purchase, this Refund &amp; Cancellation Policy governs all purchases made through the Research Spectrum platform.
                </p>
                <p>
                  By purchasing any course, course bundle, educational resource, certification pathway, or related offering currently made available through Research Spectrum, you acknowledge and agree to this policy.
                </p>
              </div>
            </div>
            {/* 1 */}
            <div className="policy-section" id="rp-1">
              <div className="ps-head"><div className="ps-num">1</div><div className="ps-title">Digital Product Nature</div></div>
              <div className="ps-body">
                <p>Research Spectrum provides digital educational products and services that become accessible immediately upon successful payment.</p>
                <p>Because access is granted instantly and digital content may be consumed immediately, all purchases are considered final.</p>
              </div>
            </div>
            {/* 2 */}
            <div className="policy-section" id="rp-2">
              <div className="ps-head"><div className="ps-num">2</div><div className="ps-title">No Refund Policy</div></div>
              <div className="ps-body">
                <p>Except where required by applicable law, all purchases made through Research Spectrum are non-refundable.</p>
                <p>This includes, but is not limited to:</p>
                <ul><li>Individual courses</li><li>Course bundles</li><li>Complete learning pathways</li><li>Certifications</li><li>Digital resources</li></ul>
                <p>Refunds will not be issued because:</p>
                <ul>
                  <li>A user changed their mind.</li>
                  <li>A user no longer has time to complete the course.</li>
                  <li>A user misunderstood the course description.</li>
                  <li>A user failed an assessment.</li>
                  <li>A user did not obtain a certificate.</li>
                  <li>A user did not achieve a desired academic or professional outcome.</li>
                  <li>A user did not secure publication, funding, employment, residency placement, academic acceptance, or other opportunities.</li>
                  <li>A user failed to complete the course.</li>
                  <li>A user disagrees with teaching methods or presentation style.</li>
                  <li>A user purchased the wrong course.</li>
                  <li>A user did not review the course information before purchase.</li>
                </ul>
              </div>
            </div>
            {/* 3 */}
            <div className="policy-section" id="rp-3">
              <div className="ps-head"><div className="ps-num">3</div><div className="ps-title">Course Access After Purchase</div></div>
              <div className="ps-body">
                <p>
                  Upon successful payment, users receive access to purchased content. Access to purchased content remains available in accordance with the Terms &amp; Conditions and applicable platform access policies.
                </p>
                <p>Access to digital content constitutes fulfillment of Research Spectrum's delivery obligations.</p>
              </div>
            </div>
            {/* 4 */}
            <div className="policy-section" id="rp-4">
              <div className="ps-head"><div className="ps-num">4</div><div className="ps-title">Fraudulent Purchases</div></div>
              <div className="ps-body">
                <p>Research Spectrum reserves the right, subject to the Terms &amp; Conditions, to:</p>
                <ul><li>Suspend access</li><li>Revoke certificates</li><li>Cancel enrollments</li><li>Terminate accounts</li></ul>
                <p>where purchases are suspected to involve:</p>
                <ul><li>Stolen payment methods</li><li>Unauthorized transactions</li><li>Fraudulent activity</li><li>Chargeback abuse</li><li>Payment manipulation</li></ul>
                <p>No refunds will be issued for accounts terminated due to fraud or policy violations.</p>
              </div>
            </div>
            {/* 5 */}
            <div className="policy-section" id="rp-5">
              <div className="ps-head"><div className="ps-num">5</div><div className="ps-title">Chargebacks and Payment Disputes</div></div>
              <div className="ps-body">
                <p>Initiating a chargeback, payment dispute, reversal, or similar claim after receiving access to digital content may result in, subject to the Terms &amp; Conditions:</p>
                <ul><li>Immediate suspension of access</li><li>Account termination</li><li>Certificate revocation</li><li>Loss of access to all purchased content</li></ul>
                <p>Research Spectrum reserves the right to challenge fraudulent or abusive chargebacks and provide supporting documentation to payment processors.</p>
              </div>
            </div>
            {/* 6 */}
            <div className="policy-section" id="rp-6">
              <div className="ps-head"><div className="ps-num">6</div><div className="ps-title">Cancellation of Services</div></div>
              <div className="ps-body">
                <p>Research Spectrum does not currently operate on a subscription model.</p>
                <p>As a result:</p>
                <ul>
                  <li>There are no recurring subscription charges to cancel.</li>
                  <li>Purchased courses remain available in accordance with the Terms &amp; Conditions.</li>
                  <li>Users may discontinue use of the platform at any time.</li>
                  <li>Discontinuing use does not create eligibility for a refund.</li>
                </ul>
              </div>
            </div>
            {/* 7 */}
            <div className="policy-section" id="rp-7">
              <div className="ps-head"><div className="ps-num">7</div><div className="ps-title">Future Services</div></div>
              <div className="ps-body">
                <p>Research Spectrum may introduce subscription products, workshops, mentorship programs, consultations, live educational events, or other services in the future.</p>
                <p>Separate refund and cancellation terms may apply to such offerings and will be published at the time those services become available.</p>
                <p>Research Spectrum reserves the right to publish additional policies governing any future products or services.</p>
              </div>
            </div>
            {/* 8 */}
            <div className="policy-section" id="rp-8">
              <div className="ps-head"><div className="ps-num">8</div><div className="ps-title">Exceptional Circumstances</div></div>
              <div className="ps-body">
                <p>Where required by applicable law, Research Spectrum may provide remedies, refunds, or other resolutions as legally required.</p>
                <p>Any such remedy shall be determined in accordance with applicable legal obligations.</p>
                <p>Nothing in this policy limits rights that cannot legally be excluded under applicable law.</p>
              </div>
            </div>
            {/* 9 */}
            <div className="policy-section" id="rp-9">
              <div className="ps-head"><div className="ps-num">9</div><div className="ps-title">Policy Changes</div></div>
              <div className="ps-body">
                <p>Research Spectrum reserves the right to modify this Refund &amp; Cancellation Policy at any time.</p>
                <p>Updated versions will be published on the website.</p>
                <p>Continued use of Research Spectrum Services following publication of updated policies constitutes acceptance of the revised policy.</p>
                <p>Research Spectrum may additionally notify users of significant changes via email.</p>
              </div>
            </div>
            {/* 10 */}
            <div className="policy-section" id="rp-10">
              <div className="ps-head"><div className="ps-num">10</div><div className="ps-title">Language</div></div>
              <div className="ps-body">
                <p>This policy may be provided in multiple languages.</p>
                <p>In the event of any discrepancy, inconsistency, conflict, or ambiguity between language versions, the English version shall prevail.</p>
              </div>
            </div>
            {/* 11 */}
            <div className="policy-section" id="rp-11">
              <div className="ps-head"><div className="ps-num">11</div><div className="ps-title">Contact</div></div>
              <div className="ps-body">
                <p>For questions regarding this Refund &amp; Cancellation Policy, please contact:</p>
                <div className="ps-contact-card">
                  <div className="ps-cc-ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  </div>
                  <div>
                    <div className="ps-cc-label">Policy Contact</div>
                    <div className="ps-cc-val"><a href="mailto:support@researchspectrum.org">support@researchspectrum.org</a></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          {/* /policy-content */}
          {/* RELATED POLICIES */}
          <div className="related-section">
            <div style={{ textAlign: "center", marginBottom: "32px" }}>
              <p style={{ fontSize: "13px", fontWeight: "700", letterSpacing: ".12em", textTransform: "uppercase", color: "var(--blue)", marginBottom: "12px" }}>Legal Documents</p>
              <h2 style={{ fontSize: "clamp(22px,3vw,32px)", fontWeight: "800", letterSpacing: "-.025em", color: "var(--ink)" }}>Related Policies</h2>
            </div>
            <div className="related-grid">
              <Link to="/terms" className="related-card">
                <div className="rc-ic">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                </div>
                <div className="rc-title">Terms &amp; Conditions</div>
                <div className="rc-sub">Platform usage rules and user responsibilities.</div>
              </Link>
              <Link to="/privacy" className="related-card">
                <div className="rc-ic">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <div className="rc-title">Privacy Policy</div>
                <div className="rc-sub">How personal information is collected, used, and protected.</div>
              </Link>
              <Link to="/delivery" className="related-card">
                <div className="rc-ic">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                </div>
                <div className="rc-title">Delivery Policy</div>
                <div className="rc-sub">How course access, certifications, and digital services are delivered.</div>
              </Link>
              <Link to="/educational-disclaimer" className="related-card">
                <div className="rc-ic">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                </div>
                <div className="rc-title">Educational Disclaimer</div>
                <div className="rc-sub">Limitations of outcomes, certifications, and educational content.</div>
              </Link>
            </div>
          </div>
          {/* /related-section */}
        </div>
        {/* /policy-main */}
      </div>
      {/* /policy-layout */}
    </div>
  )
}
