import { useRef } from 'react'
import { Link } from 'react-router-dom'

import { usePageTitle } from '../../lib/page-title'
import { usePolicySidebar } from './usePolicySidebar'
import './EducationalDisclaimerPage.css'

export default function EducationalDisclaimerPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  usePageTitle("Educational Disclaimer")
  usePolicySidebar(rootRef)

  return (
    <div ref={rootRef} className="pg-disclaimer text-rs-ink">
      <section className="pp-hero">
        <div className="wrap">
          <div className="eyebrow"><span className="dot" />Educational Disclaimer</div>
          <h1 style={{ marginTop: "16px" }}>Research Spectrum<br />Educational Disclaimer</h1>
          <p className="sub">
            Review important information regarding the educational nature of Research Spectrum services, limitations of outcomes, certificates, research opportunities, and user responsibilities.
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
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
              Educational Purpose
            </span>
            <span className="pp-meta-pill">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              No Guaranteed Outcomes
            </span>
          </div>
          <div className="legal-notice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>
              This Educational Disclaimer explains the scope, limitations, and intended educational purpose of Research Spectrum services and should be reviewed periodically for updates. Continued use of Research Spectrum Services following publication of an updated Disclaimer constitutes acceptance of the revised Disclaimer.
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
            <nav className="sidebar-nav" id="sidebarNav" aria-label="Disclaimer sections">
              <button className="sidebar-link" data-target="ed-1" type="button"><span className="sl-num">1.</span>Purpose of This Disclaimer</button>
              <button className="sidebar-link" data-target="ed-2" type="button"><span className="sl-num">2.</span>No Guarantee of Outcomes</button>
              <button className="sidebar-link" data-target="ed-3" type="button"><span className="sl-num">3.</span>Educational Content Only</button>
              <button className="sidebar-link" data-target="ed-4" type="button"><span className="sl-num">4.</span>Research Collaboration Opportunities</button>
              <button className="sidebar-link" data-target="ed-5" type="button"><span className="sl-num">5.</span>Certificates</button>
              <button className="sidebar-link" data-target="ed-6" type="button"><span className="sl-num">6.</span>Accuracy of Information</button>
              <button className="sidebar-link" data-target="ed-7" type="button"><span className="sl-num">7.</span>User Responsibility</button>
              <button className="sidebar-link" data-target="ed-8" type="button"><span className="sl-num">8.</span>Third-Party Resources</button>
              <button className="sidebar-link" data-target="ed-9" type="button"><span className="sl-num">9.</span>Limitation of Reliance</button>
              <button className="sidebar-link" data-target="ed-10" type="button"><span className="sl-num">10.</span>Limitation of Liability</button>
              <button className="sidebar-link" data-target="ed-11" type="button"><span className="sl-num">11.</span>Changes to This Disclaimer</button>
              <button className="sidebar-link" data-target="ed-12" type="button"><span className="sl-num">12.</span>Language</button>
              <button className="sidebar-link" data-target="ed-13" type="button"><span className="sl-num">13.</span>Contact</button>
            </nav>
          </div>
        </aside>
        {/* CONTENT */}
        <div className="policy-main">
          <div className="policy-content">
            {/* 1 */}
            <div className="policy-section" id="ed-1">
              <div className="ps-head"><div className="ps-num">1</div><div className="ps-title">Purpose of This Disclaimer</div></div>
              <div className="ps-body">
                <p>
                  The courses, assessments, certifications, educational materials, educational resources, and other currently available Services provided by Research Spectrum are intended solely for educational and informational purposes.
                </p>
                <p>By accessing or using Research Spectrum Services, you acknowledge and agree to this Disclaimer.</p>
              </div>
            </div>
            {/* 2 */}
            <div className="policy-section" id="ed-2">
              <div className="ps-head"><div className="ps-num">2</div><div className="ps-title">No Guarantee of Outcomes</div></div>
              <div className="ps-body">
                <p>Research Spectrum makes no guarantees, representations, or warranties regarding any specific outcome resulting from the use of its Services.</p>
                <p>Research Spectrum does not guarantee:</p>
                <ul>
                  <li>Publication of manuscripts</li>
                  <li>Acceptance of research papers</li>
                  <li>Journal acceptance</li>
                  <li>Residency placement</li>
                  <li>Employment opportunities</li>
                  <li>Promotions</li>
                  <li>Academic success</li>
                  <li>Examination success</li>
                  <li>Research funding</li>
                  <li>Grant awards</li>
                  <li>Scholarship awards</li>
                  <li>Acceptance into educational programs</li>
                  <li>Research collaboration opportunities</li>
                  <li>Professional advancement</li>
                  <li>Any specific educational, academic, financial, professional, or personal outcome</li>
                </ul>
                <p>Individual results vary based on numerous factors beyond the control of Research Spectrum.</p>
              </div>
            </div>
            {/* 3 */}
            <div className="policy-section" id="ed-3">
              <div className="ps-head"><div className="ps-num">3</div><div className="ps-title">Educational Content Only</div></div>
              <div className="ps-body">
                <p>All content provided through Research Spectrum is educational in nature.</p>
                <p>Content should not be interpreted as:</p>
                <ul>
                  <li>Medical advice</li>
                  <li>Legal advice</li>
                  <li>Financial advice</li>
                  <li>Regulatory advice</li>
                  <li>Professional advice</li>
                  <li>Institutional guidance</li>
                  <li>Academic accreditation</li>
                  <li>Career counseling</li>
                </ul>
                <p>Users should consult appropriately qualified professionals before making decisions based on information obtained through the Services.</p>
              </div>
            </div>
            {/* 4 */}
            <div className="policy-section" id="ed-4">
              <div className="ps-head"><div className="ps-num">4</div><div className="ps-title">Research Collaboration Opportunities</div></div>
              <div className="ps-body">
                <p>Research Spectrum may, at its sole discretion, offer:</p>
                <ul>
                  <li>Research collaboration opportunities</li>
                  <li>Mentorship opportunities</li>
                  <li>Project participation opportunities</li>
                  <li>Academic initiatives</li>
                  <li>Educational opportunities</li>
                </ul>
                <p>to selected individuals.</p>
                <p>Such opportunities are entirely discretionary.</p>
                <p>
                  Completion of required pathway requirements may make a user eligible to apply for certain opportunities offered by Research Spectrum. Eligibility to apply does not guarantee invitation, selection, acceptance, participation, authorship, project assignment, mentorship, collaboration opportunities, or project availability.
                </p>
                <p>Research Spectrum reserves the sole right to determine:</p>
                <ul><li>Eligibility criteria</li><li>Selection criteria</li><li>Project availability</li><li>Participant capacity</li><li>Participation requirements</li></ul>
                <p>at any time.</p>
              </div>
            </div>
            {/* 5 */}
            <div className="policy-section" id="ed-5">
              <div className="ps-head"><div className="ps-num">5</div><div className="ps-title">Certificates</div></div>
              <div className="ps-body">
                <p>
                  Certificates issued by Research Spectrum verify completion of Research Spectrum educational and assessment requirements and reflect successful completion of platform-defined competency requirements.
                </p>
                <p>Certificates do not constitute:</p>
                <ul>
                  <li>Academic credit</li>
                  <li>University accreditation</li>
                  <li>Professional licensure</li>
                  <li>Professional certification</li>
                  <li>Government recognition</li>
                  <li>Institutional endorsement</li>
                </ul>
                <p>
                  Research Spectrum certificates confirm that a user has met Research Spectrum's defined learning and assessment standards. They should not be interpreted as a substitute for accredited academic qualifications, government-recognised professional certifications, or professional licenses issued by regulatory bodies.
                </p>
              </div>
            </div>
            {/* 6 */}
            <div className="policy-section" id="ed-6">
              <div className="ps-head"><div className="ps-num">6</div><div className="ps-title">Accuracy of Information</div></div>
              <div className="ps-body">
                <p>Research Spectrum strives to provide accurate and up-to-date educational content.</p>
                <p>However, Research Spectrum does not warrant that:</p>
                <ul>
                  <li>All content is complete</li>
                  <li>All content is error-free</li>
                  <li>All content is current</li>
                  <li>All content reflects the latest developments</li>
                  <li>All content is suitable for every user or situation</li>
                </ul>
                <p>Educational content may be updated, revised, expanded, modified, reorganized, or corrected at any time.</p>
              </div>
            </div>
            {/* 7 */}
            <div className="policy-section" id="ed-7">
              <div className="ps-head"><div className="ps-num">7</div><div className="ps-title">User Responsibility</div></div>
              <div className="ps-body">
                <p>Users remain solely responsible for:</p>
                <ul>
                  <li>Decisions made using information obtained from Research Spectrum</li>
                  <li>Research conducted using information obtained from Research Spectrum</li>
                  <li>Academic work prepared using information obtained from Research Spectrum</li>
                  <li>Professional actions taken based on educational content</li>
                </ul>
                <p>Research Spectrum shall not be responsible for decisions, actions, omissions, or outcomes arising from the use of the Services.</p>
              </div>
            </div>
            {/* 8 */}
            <div className="policy-section" id="ed-8">
              <div className="ps-head"><div className="ps-num">8</div><div className="ps-title">Third-Party Resources</div></div>
              <div className="ps-body">
                <p>Research Spectrum may reference, discuss, link to, or mention third-party resources, software, journals, databases, websites, tools, services, organizations, or platforms.</p>
                <p>Such references do not constitute endorsement.</p>
                <p>Research Spectrum is not responsible for:</p>
                <ul><li>Third-party content</li><li>Third-party policies</li><li>Third-party services</li><li>Third-party availability</li><li>Third-party accuracy</li></ul>
              </div>
            </div>
            {/* 9 */}
            <div className="policy-section" id="ed-9">
              <div className="ps-head"><div className="ps-num">9</div><div className="ps-title">Limitation of Reliance</div></div>
              <div className="ps-body">
                <p>
                  Users acknowledge that educational content provided through Research Spectrum is intended to supplement learning and should not be relied upon as the sole basis for academic, professional, legal, medical, financial, or research decisions.
                </p>
              </div>
            </div>
            {/* 10 */}
            <div className="policy-section" id="ed-10">
              <div className="ps-head"><div className="ps-num">10</div><div className="ps-title">Limitation of Liability</div></div>
              <div className="ps-body">
                <p>To the fullest extent permitted by applicable law, Research Spectrum shall not be liable for:</p>
                <ul>
                  <li>Direct damages</li>
                  <li>Indirect damages</li>
                  <li>Incidental damages</li>
                  <li>Consequential damages</li>
                  <li>Special damages</li>
                  <li>Loss of opportunities</li>
                  <li>Loss of funding</li>
                  <li>Loss of employment</li>
                  <li>Academic outcomes</li>
                  <li>Research outcomes</li>
                  <li>Publication outcomes</li>
                  <li>Business losses</li>
                </ul>
                <p>arising from or relating to the use of the Services.</p>
              </div>
            </div>
            {/* 11 */}
            <div className="policy-section" id="ed-11">
              <div className="ps-head"><div className="ps-num">11</div><div className="ps-title">Changes to This Disclaimer</div></div>
              <div className="ps-body">
                <p>Research Spectrum reserves the right to modify this Disclaimer at any time.</p>
                <p>Updated versions will be published on the website.</p>
                <p>Continued use of Research Spectrum Services following publication of an updated Disclaimer constitutes acceptance of the revised Disclaimer.</p>
                <p>Research Spectrum may additionally notify users of significant changes via email.</p>
              </div>
            </div>
            {/* 12 */}
            <div className="policy-section" id="ed-12">
              <div className="ps-head"><div className="ps-num">12</div><div className="ps-title">Language</div></div>
              <div className="ps-body">
                <p>This Disclaimer may be provided in multiple languages.</p>
                <p>In the event of any discrepancy, inconsistency, conflict, or ambiguity between language versions, the English version shall prevail.</p>
              </div>
            </div>
            {/* 13 */}
            <div className="policy-section" id="ed-13">
              <div className="ps-head"><div className="ps-num">13</div><div className="ps-title">Contact</div></div>
              <div className="ps-body">
                <p>For questions regarding this Disclaimer, please contact:</p>
                <div className="ps-contact-card">
                  <div className="ps-cc-ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  </div>
                  <div>
                    <div className="ps-cc-label">Disclaimer Contact</div>
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
