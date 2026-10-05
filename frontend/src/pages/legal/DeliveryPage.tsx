import { useRef } from 'react'
import { Link } from 'react-router-dom'

import { usePageTitle } from '../../lib/page-title'
import { usePolicySidebar } from './usePolicySidebar'
import './DeliveryPage.css'

export default function DeliveryPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  usePageTitle("Delivery Policy")
  usePolicySidebar(rootRef)

  return (
    <div ref={rootRef} className="pg-delivery text-rs-ink">
      <section className="pp-hero">
        <div className="wrap">
          <div className="eyebrow"><span className="dot" />Delivery Policy</div>
          <h1 style={{ marginTop: "16px" }}>Research Spectrum<br />Delivery Policy</h1>
          <p className="sub">Learn how access to Research Spectrum courses, course bundles, educational resources, assessments, and certifications is delivered to users.</p>
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
                <rect x="2" y="3" width="20" height="14" rx="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
              Digital Delivery Only
            </span>
            <span className="pp-meta-pill">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              Immediate Course Access
            </span>
          </div>
          <div className="legal-notice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>
              This Delivery Policy governs how Research Spectrum products and services are delivered and should be reviewed periodically for updates. Continued use of the Services following publication of updated policies constitutes acceptance of the revised policy.
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
              <button className="sidebar-link" data-target="dp-intro" type="button"><span className="sl-num">—</span>Introduction</button>
              <button className="sidebar-link" data-target="dp-1" type="button"><span className="sl-num">1.</span>Nature of Products</button>
              <button className="sidebar-link" data-target="dp-2" type="button"><span className="sl-num">2.</span>Delivery Method</button>
              <button className="sidebar-link" data-target="dp-3" type="button"><span className="sl-num">3.</span>Delivery Timeframe</button>
              <button className="sidebar-link" data-target="dp-4" type="button"><span className="sl-num">4.</span>Technical Access Issues</button>
              <button className="sidebar-link" data-target="dp-5" type="button"><span className="sl-num">5.</span>User Responsibilities</button>
              <button className="sidebar-link" data-target="dp-6" type="button"><span className="sl-num">6.</span>Device Restrictions</button>
              <button className="sidebar-link" data-target="dp-7" type="button"><span className="sl-num">7.</span>Availability of Content</button>
              <button className="sidebar-link" data-target="dp-8" type="button"><span className="sl-num">8.</span>International Delivery</button>
              <button className="sidebar-link" data-target="dp-9" type="button"><span className="sl-num">9.</span>Future Services</button>
              <button className="sidebar-link" data-target="dp-10" type="button"><span className="sl-num">10.</span>Force Majeure</button>
              <button className="sidebar-link" data-target="dp-11" type="button"><span className="sl-num">11.</span>Policy Changes</button>
              <button className="sidebar-link" data-target="dp-12" type="button"><span className="sl-num">12.</span>Language</button>
              <button className="sidebar-link" data-target="dp-13" type="button"><span className="sl-num">13.</span>Contact</button>
            </nav>
          </div>
        </aside>
        {/* CONTENT */}
        <div className="policy-main">
          <div className="policy-content">
            {/* Intro */}
            <div className="policy-intro-section" id="dp-intro">
              <div className="pi-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
                Delivery Policy
              </div>
              <div className="ps-body">
                <p>Research Spectrum provides digital educational content and services through an online learning platform.</p>
                <p>This Delivery Policy explains how access to purchased products and services is delivered to users.</p>
              </div>
            </div>
            {/* 1 */}
            <div className="policy-section" id="dp-1">
              <div className="ps-head"><div className="ps-num">1</div><div className="ps-title">Nature of Products</div></div>
              <div className="ps-body">
                <p>Research Spectrum currently offers the following digital products:</p>
                <ul><li>Online courses</li><li>Course bundles</li><li>Educational resources</li><li>Assessments</li><li>Certifications</li></ul>
                <p>No physical products are shipped or delivered.</p>
              </div>
            </div>
            {/* 2 */}
            <div className="policy-section" id="dp-2">
              <div className="ps-head"><div className="ps-num">2</div><div className="ps-title">Delivery Method</div></div>
              <div className="ps-body">
                <p>All products and services are delivered electronically through the Research Spectrum platform.</p>
                <p>Upon successful payment, eligible users will receive access to purchased content through their Research Spectrum account.</p>
                <p>Delivery occurs through:</p>
                <ul><li>Website access</li><li>User dashboard access</li><li>Online learning platform access</li><li>Electronic communications where applicable</li></ul>
              </div>
            </div>
            {/* 3 */}
            <div className="policy-section" id="dp-3">
              <div className="ps-head"><div className="ps-num">3</div><div className="ps-title">Delivery Timeframe</div></div>
              <div className="ps-body">
                <p>Access to purchased courses and digital content is typically granted automatically and immediately following successful payment confirmation.</p>
                <p>In rare circumstances involving:</p>
                <ul><li>Payment verification</li><li>Technical issues</li><li>System maintenance</li><li>Security reviews</li><li>Third-party service interruptions</li></ul>
                <p>delivery may be delayed.</p>
                <p>Research Spectrum will make reasonable efforts to resolve such issues promptly.</p>
              </div>
            </div>
            {/* 4 */}
            <div className="policy-section" id="dp-4">
              <div className="ps-head"><div className="ps-num">4</div><div className="ps-title">Technical Access Issues</div></div>
              <div className="ps-body">
                <p>If payment is successfully completed but access to purchased content is not granted, users should contact:</p>
                <div className="ps-contact-card" style={{ margin: "12px 0 16px" }}>
                  <div className="ps-cc-ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  </div>
                  <div>
                    <div className="ps-cc-label">Access Support</div>
                    <div className="ps-cc-val"><a href="mailto:support@researchspectrum.org">support@researchspectrum.org</a></div>
                  </div>
                </div>
                <p>Research Spectrum will make reasonable efforts to investigate and restore access in a timely manner.</p>
              </div>
            </div>
            {/* 5 */}
            <div className="policy-section" id="dp-5">
              <div className="ps-head"><div className="ps-num">5</div><div className="ps-title">User Responsibilities</div></div>
              <div className="ps-body">
                <p>Users are responsible for:</p>
                <ul>
                  <li>Providing accurate account information</li>
                  <li>Maintaining access to their registered email address</li>
                  <li>Maintaining internet connectivity</li>
                  <li>Using compatible devices and software</li>
                  <li>Protecting account credentials</li>
                </ul>
                <p>Research Spectrum is not responsible for access issues resulting from:</p>
                <ul>
                  <li>Incorrect account information</li>
                  <li>User device problems</li>
                  <li>Internet connectivity issues</li>
                  <li>Third-party software conflicts</li>
                  <li>Unauthorized account sharing</li>
                </ul>
              </div>
            </div>
            {/* 6 */}
            <div className="policy-section" id="dp-6">
              <div className="ps-head"><div className="ps-num">6</div><div className="ps-title">Device Restrictions</div></div>
              <div className="ps-body">
                <p>Access to purchased content is subject to platform licensing restrictions, including:</p>
                <ul><li>Maximum of three (3) registered devices per account</li><li>One (1) active session at a time</li><li>Technical measures used to protect intellectual property</li></ul>
                <p>These restrictions form part of the delivery and access model of Research Spectrum Services.</p>
              </div>
            </div>
            {/* 7 */}
            <div className="policy-section" id="dp-7">
              <div className="ps-head"><div className="ps-num">7</div><div className="ps-title">Availability of Content</div></div>
              <div className="ps-body">
                <p>
                  Access to purchased courses remains available for as long as Research Spectrum continues to operate the applicable course and platform, subject to the Terms &amp; Conditions. Course access is licensed, not sold, and is not guaranteed in perpetuity independent of platform operation.
                </p>
                <p>Research Spectrum reserves the right to:</p>
                <ul>
                  <li>Modify courses</li>
                  <li>Update content</li>
                  <li>Reorganize modules</li>
                  <li>Add or remove educational materials</li>
                  <li>Improve course structures</li>
                  <li>Retire unsupported courses</li>
                </ul>
                <p>at its sole discretion.</p>
              </div>
            </div>
            {/* 8 */}
            <div className="policy-section" id="dp-8">
              <div className="ps-head"><div className="ps-num">8</div><div className="ps-title">International Delivery</div></div>
              <div className="ps-body">
                <p>Because Research Spectrum delivers content electronically, Services may generally be accessed internationally where legally permitted.</p>
                <p>Users are responsible for complying with local laws and regulations applicable in their jurisdiction.</p>
              </div>
            </div>
            {/* 9 */}
            <div className="policy-section" id="dp-9">
              <div className="ps-head"><div className="ps-num">9</div><div className="ps-title">Future Services</div></div>
              <div className="ps-body">
                <p>Research Spectrum may introduce additional services in the future. These may include, but are not limited to:</p>
                <ul><li>Live workshops</li><li>Mentorship sessions</li><li>Consultations</li><li>Interactive educational events</li></ul>
                <p>
                  None of the above are currently available. Where such services are introduced, their specific delivery methods, access requirements, and terms will be communicated on the applicable product page at the time of launch.
                </p>
              </div>
            </div>
            {/* 10 */}
            <div className="policy-section" id="dp-10">
              <div className="ps-head"><div className="ps-num">10</div><div className="ps-title">Force Majeure</div></div>
              <div className="ps-body">
                <p>Research Spectrum shall not be responsible for delays or interruptions in delivery caused by events beyond its reasonable control, including:</p>
                <ul>
                  <li>Internet outages</li>
                  <li>Cybersecurity incidents</li>
                  <li>Government restrictions</li>
                  <li>Natural disasters</li>
                  <li>Infrastructure failures</li>
                  <li>Third-party service outages</li>
                </ul>
              </div>
            </div>
            {/* 11 */}
            <div className="policy-section" id="dp-11">
              <div className="ps-head"><div className="ps-num">11</div><div className="ps-title">Policy Changes</div></div>
              <div className="ps-body">
                <p>Research Spectrum reserves the right to modify this Delivery Policy at any time.</p>
                <p>Updated versions will be published on the website.</p>
                <p>Continued use of the Services following publication of updated policies constitutes acceptance of the revised policy.</p>
                <p>Research Spectrum may additionally notify users of significant changes via email.</p>
              </div>
            </div>
            {/* 12 */}
            <div className="policy-section" id="dp-12">
              <div className="ps-head"><div className="ps-num">12</div><div className="ps-title">Language</div></div>
              <div className="ps-body">
                <p>This policy may be provided in multiple languages.</p>
                <p>In the event of any discrepancy, inconsistency, conflict, or ambiguity between language versions, the English version shall prevail.</p>
              </div>
            </div>
            {/* 13 */}
            <div className="policy-section" id="dp-13">
              <div className="ps-head"><div className="ps-num">13</div><div className="ps-title">Contact</div></div>
              <div className="ps-body">
                <p>For questions regarding this Delivery Policy, please contact:</p>
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
              <Link to="/refund" className="related-card">
                <div className="rc-ic">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                    <path d="M3 3v5h5" />
                  </svg>
                </div>
                <div className="rc-title">Refund Policy</div>
                <div className="rc-sub">Purchase, cancellation, and refund eligibility terms.</div>
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
