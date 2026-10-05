import { useRef } from 'react'
import { Link } from 'react-router-dom'

import { usePageTitle } from '../../lib/page-title'
import { usePolicySidebar } from './usePolicySidebar'
import './TermsPage.css'

export default function TermsPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  usePageTitle("Terms & Conditions")
  usePolicySidebar(rootRef)

  return (
    <div ref={rootRef} className="pg-terms text-rs-ink">
      <section className="pp-hero">
        <div className="wrap">
          <div className="eyebrow"><span className="dot" />Terms &amp; Conditions</div>
          <h1 style={{ marginTop: "16px" }}>Research Spectrum<br />Terms &amp; Conditions</h1>
          <p className="sub">Review the terms governing access to Research Spectrum courses, educational services, assessments, certificates, accounts, and platform resources.</p>
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
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Platform Rules
            </span>
          </div>
          <div className="legal-notice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>
              These Terms &amp; Conditions govern access to and use of Research Spectrum services and should be reviewed periodically for updates. Continued use of the Services following publication of updated Terms constitutes acceptance of the revised Terms.
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
            <nav className="sidebar-nav" id="sidebarNav" aria-label="Terms sections">
              <button className="sidebar-link" data-target="ts-intro" type="button"><span className="sl-num">—</span>Introduction</button>
              <button className="sidebar-link" data-target="ts-1" type="button"><span className="sl-num">1.</span>Eligibility</button>
              <button className="sidebar-link" data-target="ts-2" type="button"><span className="sl-num">2.</span>Educational Purpose</button>
              <button className="sidebar-link" data-target="ts-3" type="button"><span className="sl-num">3.</span>License to Access Content</button>
              <button className="sidebar-link" data-target="ts-4" type="button"><span className="sl-num">4.</span>Course Access</button>
              <button className="sidebar-link" data-target="ts-5" type="button"><span className="sl-num">5.</span>Account Registration</button>
              <button className="sidebar-link" data-target="ts-6" type="button"><span className="sl-num">6.</span>Device &amp; Session Restrictions</button>
              <button className="sidebar-link" data-target="ts-7" type="button"><span className="sl-num">7.</span>Prohibited Conduct</button>
              <button className="sidebar-link" data-target="ts-8" type="button"><span className="sl-num">8.</span>Assessments &amp; Certification</button>
              <button className="sidebar-link" data-target="ts-9" type="button"><span className="sl-num">9.</span>Academic Integrity</button>
              <button className="sidebar-link" data-target="ts-10" type="button"><span className="sl-num">10.</span>Certificate Ownership</button>
              <button className="sidebar-link" data-target="ts-11" type="button"><span className="sl-num">11.</span>Research Opportunities</button>
              <button className="sidebar-link" data-target="ts-12" type="button"><span className="sl-num">12.</span>Reviews &amp; Testimonials</button>
              <button className="sidebar-link" data-target="ts-13" type="button"><span className="sl-num">13.</span>Payments</button>
              <button className="sidebar-link" data-target="ts-14" type="button"><span className="sl-num">14.</span>Chargebacks</button>
              <button className="sidebar-link" data-target="ts-15" type="button"><span className="sl-num">15.</span>Account Suspension</button>
              <button className="sidebar-link" data-target="ts-16" type="button"><span className="sl-num">16.</span>Platform Availability</button>
              <button className="sidebar-link" data-target="ts-17" type="button"><span className="sl-num">17.</span>Beta Features</button>
              <button className="sidebar-link" data-target="ts-18" type="button"><span className="sl-num">18.</span>Copyright Enforcement</button>
              <button className="sidebar-link" data-target="ts-19" type="button"><span className="sl-num">19.</span>Policy Changes</button>
              <button className="sidebar-link" data-target="ts-20" type="button"><span className="sl-num">20.</span>Force Majeure</button>
              <button className="sidebar-link" data-target="ts-21" type="button"><span className="sl-num">21.</span>Governing Law</button>
              <button className="sidebar-link" data-target="ts-22" type="button"><span className="sl-num">22.</span>Language</button>
              <button className="sidebar-link" data-target="ts-23" type="button"><span className="sl-num">23.</span>Contact</button>
            </nav>
          </div>
        </aside>
        {/* CONTENT */}
        <div className="policy-main">
          <div className="policy-content">
            {/* Introduction */}
            <div className="policy-intro-section" id="ts-intro">
              <div className="pi-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                Terms &amp; Conditions
              </div>
              <div className="ps-body">
                <p>
                  Welcome to Research Spectrum. These Terms &amp; Conditions ("Terms") govern your access to and use of the Research Spectrum website, platform, courses, assessments, certifications, educational resources, digital content, and related services currently made available through Research Spectrum (collectively, the "Services").
                </p>
                <p>By accessing, registering for, purchasing, or using any Research Spectrum Services, you acknowledge that you have read, understood, and agreed to be bound by these Terms.</p>
              </div>
              <div className="pi-operator">
                <b>Operator:</b>
                Research Spectrum is operated by Bahaa Aburayya for Electronic Shopping, a sole proprietorship registered in the Hashemite Kingdom of Jordan.
              </div>
            </div>
            {/* 1 */}
            <div className="policy-section" id="ts-1">
              <div className="ps-head"><div className="ps-num">1</div><div className="ps-title">Eligibility</div></div>
              <div className="ps-body">
                <p>You must be at least eighteen (18) years old, or the age of majority in your jurisdiction, to purchase or use Research Spectrum Services.</p>
                <p>By using the Services, you represent and warrant that you meet these eligibility requirements.</p>
              </div>
            </div>
            {/* 2 */}
            <div className="policy-section" id="ts-2">
              <div className="ps-head"><div className="ps-num">2</div><div className="ps-title">Educational Purpose</div></div>
              <div className="ps-body">
                <p>All content provided through Research Spectrum is intended solely for educational and informational purposes.</p>
                <p>Research Spectrum does not provide medical, legal, financial, regulatory, academic, professional, or other professional advice.</p>
                <p>Research Spectrum does not guarantee:</p>
                <ul>
                  <li>Publication of manuscripts</li>
                  <li>Acceptance into educational programs</li>
                  <li>Residency placement</li>
                  <li>Employment</li>
                  <li>Promotions</li>
                  <li>Grants</li>
                  <li>Funding opportunities</li>
                  <li>Academic success</li>
                  <li>Research success</li>
                  <li>Any specific outcome</li>
                </ul>
                <p>Individual results depend on numerous factors beyond the control of Research Spectrum.</p>
              </div>
            </div>
            {/* 3 */}
            <div className="policy-section" id="ts-3">
              <div className="ps-head"><div className="ps-num">3</div><div className="ps-title">License to Access Content</div></div>
              <div className="ps-body">
                <p>All course materials, videos, assessments, quizzes, certificates, resources, PDFs, graphics, presentations, and other content are licensed, not sold.</p>
                <p>Purchasing a course grants you a limited, non-exclusive, non-transferable, revocable license to access the purchased content in accordance with these Terms.</p>
                <p>No ownership rights are transferred to you.</p>
              </div>
            </div>
            {/* 4 */}
            <div className="policy-section" id="ts-4">
              <div className="ps-head"><div className="ps-num">4</div><div className="ps-title">Course Access</div></div>
              <div className="ps-body">
                <p>Purchased courses include lifetime access for the operational lifetime of the purchased course while it remains offered and supported by Research Spectrum.</p>
                <p>Research Spectrum reserves the right to:</p>
                <ul>
                  <li>Modify courses</li>
                  <li>Update content</li>
                  <li>Add lectures</li>
                  <li>Remove lectures</li>
                  <li>Reorganize modules</li>
                  <li>Improve course materials</li>
                  <li>Replace content</li>
                  <li>Retire courses</li>
                  <li>Discontinue support for courses</li>
                </ul>
                <p>at its sole discretion.</p>
              </div>
            </div>
            {/* 5 */}
            <div className="policy-section" id="ts-5">
              <div className="ps-head"><div className="ps-num">5</div><div className="ps-title">Account Registration</div></div>
              <div className="ps-body">
                <p>Users must provide accurate and complete information when creating an account.</p>
                <p>You are responsible for maintaining the confidentiality of your login credentials.</p>
                <p>You are solely responsible for all activities occurring under your account.</p>
                <p>You must immediately notify Research Spectrum of any suspected unauthorized use of your account.</p>
              </div>
            </div>
            {/* 6 */}
            <div className="policy-section" id="ts-6">
              <div className="ps-head"><div className="ps-num">6</div><div className="ps-title">Device and Session Restrictions</div></div>
              <div className="ps-body">
                <p>Access to Research Spectrum content is subject to the following restrictions:</p>
                <ul>
                  <li>Maximum of three (3) registered devices per account.</li>
                  <li>One (1) active session at a time.</li>
                  <li>Device limitations may be enforced through technical measures.</li>
                  <li>Research Spectrum may collect technical information to enforce licensing restrictions and protect intellectual property.</li>
                </ul>
                <p>Accounts may not be transferred, sold, leased, shared, assigned, or otherwise made available to another person.</p>
              </div>
            </div>
            {/* 7 */}
            <div className="policy-section" id="ts-7">
              <div className="ps-head"><div className="ps-num">7</div><div className="ps-title">Prohibited Conduct</div></div>
              <div className="ps-body">
                <p>Users may not:</p>
                <ul>
                  <li>Share account credentials.</li>
                  <li>Permit others to access purchased content.</li>
                  <li>Sell, transfer, or assign accounts.</li>
                  <li>Record videos for redistribution.</li>
                  <li>Circumvent technical protections.</li>
                  <li>Download content using unauthorized methods.</li>
                  <li>Copy or reproduce course materials.</li>
                  <li>Redistribute PDFs or educational resources.</li>
                  <li>Upload content to public or private platforms.</li>
                  <li>Create derivative courses or competing educational products.</li>
                  <li>Use course content to train, fine-tune, develop, evaluate, improve, or support artificial intelligence or machine learning systems.</li>
                  <li>Engage in harassment, abuse, impersonation, fraud, or unlawful conduct.</li>
                  <li>Reverse engineer platform functionality.</li>
                  <li>Attempt unauthorized access to systems or data.</li>
                </ul>
              </div>
            </div>
            {/* 8 */}
            <div className="policy-section" id="ts-8">
              <div className="ps-head"><div className="ps-num">8</div><div className="ps-title">Assessments and Certification</div></div>
              <div className="ps-body">
                <p>To obtain a certificate:</p>
                <ul>
                  <li>100% course completion is required.</li>
                  <li>A minimum score of 70% must be achieved on every required module quiz.</li>
                  <li>A minimum score of 70% must be achieved on the final assessment.</li>
                  <li>All mandatory assessments must be completed.</li>
                </ul>
                <p>Users may attempt assessments an unlimited number of times.</p>
                <p>Research Spectrum reserves the right to modify:</p>
                <ul><li>Assessment structures</li><li>Passing thresholds</li><li>Certification requirements</li><li>Verification methods</li></ul>
                <p>at any time.</p>
                <p>Certificates are issued solely as evidence of completion of educational content.</p>
                <p>Certificates do not constitute:</p>
                <ul><li>Academic credit</li><li>University accreditation</li><li>Professional licensure</li><li>Employment qualifications</li><li>Professional certification</li></ul>
              </div>
            </div>
            {/* 9 */}
            <div className="policy-section" id="ts-9">
              <div className="ps-head"><div className="ps-num">9</div><div className="ps-title">Academic Integrity</div></div>
              <div className="ps-body">
                <p>Users may not:</p>
                <ul>
                  <li>Use another person to complete assessments.</li>
                  <li>Complete assessments on behalf of another person.</li>
                  <li>Use unauthorized assistance during assessments.</li>
                  <li>Use artificial intelligence systems to generate answers for quizzes, examinations, certifications, or assessments.</li>
                  <li>Manipulate assessment results.</li>
                </ul>
                <p>Research Spectrum reserves the right to invalidate:</p>
                <ul><li>Quiz results</li><li>Examination results</li><li>Certificates</li><li>Completion records</li></ul>
                <p>where misconduct is suspected or identified.</p>
              </div>
            </div>
            {/* 10 */}
            <div className="policy-section" id="ts-10">
              <div className="ps-head"><div className="ps-num">10</div><div className="ps-title">Certificate Ownership and Verification</div></div>
              <div className="ps-body">
                <p>Research Spectrum retains ownership of certificate templates, designs, verification systems, credential records, and related intellectual property.</p>
                <p>Certificates may:</p>
                <ul><li>Be verified</li><li>Be suspended</li><li>Be revoked</li><li>Be invalidated</li></ul>
                <p>at the sole discretion of Research Spectrum.</p>
                <p>Certificates may not be:</p>
                <ul><li>Sold</li><li>Transferred</li><li>Assigned</li><li>Reissued to another individual</li></ul>
              </div>
            </div>
            {/* 11 */}
            <div className="policy-section" id="ts-11">
              <div className="ps-head"><div className="ps-num">11</div><div className="ps-title">Research Opportunities</div></div>
              <div className="ps-body">
                <p>Research Spectrum may, at its sole discretion, offer research collaboration opportunities, project participation opportunities, or related opportunities to selected users.</p>
                <p>
                  Completion of pathway requirements may make a user eligible to apply for certain Research Spectrum research opportunities. Eligibility to apply does not guarantee invitation, acceptance, participation, project assignment, authorship, mentorship, selection, or availability of opportunities.
                </p>
              </div>
            </div>
            {/* 12 */}
            <div className="policy-section" id="ts-12">
              <div className="ps-head"><div className="ps-num">12</div><div className="ps-title">Reviews and Testimonials</div></div>
              <div className="ps-body">
                <p>
                  By submitting reviews, testimonials, comments, feedback, or similar content, you grant Research Spectrum a perpetual, worldwide, royalty-free, non-exclusive license to use, reproduce, display, publish, modify, and distribute such content for educational, operational, and promotional purposes.
                </p>
              </div>
            </div>
            {/* 13 */}
            <div className="policy-section" id="ts-13">
              <div className="ps-head"><div className="ps-num">13</div><div className="ps-title">Payments</div></div>
              <div className="ps-body">
                <p>All prices are displayed on the website and may be modified at any time.</p>
                <p>Payments are processed through third-party payment providers.</p>
                <p>Research Spectrum is not responsible for delays, interruptions, errors, or failures caused by third-party payment processors.</p>
                <p>Users are responsible for any taxes, duties, or fees imposed by their jurisdiction.</p>
              </div>
            </div>
            {/* 14 */}
            <div className="policy-section" id="ts-14">
              <div className="ps-head"><div className="ps-num">14</div><div className="ps-title">Chargebacks</div></div>
              <div className="ps-body">
                <p>Initiating a chargeback, payment dispute, reversal, or similar claim after receiving access to digital content may result in:</p>
                <ul><li>Immediate account suspension</li><li>Termination of account access</li><li>Revocation of certificates</li><li>Permanent loss of access to purchased content</li></ul>
                <p>pending investigation and resolution.</p>
              </div>
            </div>
            {/* 15 */}
            <div className="policy-section" id="ts-15">
              <div className="ps-head"><div className="ps-num">15</div><div className="ps-title">Account Suspension and Termination</div></div>
              <div className="ps-body">
                <p>Research Spectrum may suspend or terminate accounts for violations of these Terms.</p>
                <p>Violations may result in:</p>
                <ul>
                  <li>Suspension of access</li>
                  <li>Permanent termination</li>
                  <li>Revocation of certificates</li>
                  <li>Removal of content</li>
                  <li>Loss of all purchased content</li>
                  <li>Legal action where appropriate</li>
                </ul>
                <p>No refunds will be provided following termination resulting from violations of these Terms.</p>
              </div>
            </div>
            {/* 16 */}
            <div className="policy-section" id="ts-16">
              <div className="ps-head"><div className="ps-num">16</div><div className="ps-title">Platform Availability</div></div>
              <div className="ps-body">
                <p>Research Spectrum does not guarantee uninterrupted availability of the Services.</p>
                <p>Maintenance, updates, repairs, outages, technical issues, security events, and third-party service interruptions may temporarily affect access.</p>
              </div>
            </div>
            {/* 17 */}
            <div className="policy-section" id="ts-17">
              <div className="ps-head"><div className="ps-num">17</div><div className="ps-title">Beta Features</div></div>
              <div className="ps-body"><p>Research Spectrum may introduce, modify, suspend, or discontinue beta features at any time without liability.</p></div>
            </div>
            {/* 18 */}
            <div className="policy-section" id="ts-18">
              <div className="ps-head"><div className="ps-num">18</div><div className="ps-title">Copyright Enforcement</div></div>
              <div className="ps-body">
                <p>Research Spectrum reserves all intellectual property rights.</p>
                <p>Research Spectrum may pursue:</p>
                <ul><li>Copyright claims</li><li>DMCA-style takedown requests</li><li>Legal remedies</li><li>Account termination</li><li>Other enforcement measures</li></ul>
                <p>against unauthorized use or distribution of content.</p>
              </div>
            </div>
            {/* 19 */}
            <div className="policy-section" id="ts-19">
              <div className="ps-head"><div className="ps-num">19</div><div className="ps-title">Policy Changes</div></div>
              <div className="ps-body">
                <p>Research Spectrum reserves the right to modify these Terms at any time.</p>
                <p>Updated versions will be posted on the website.</p>
                <p>Continued use of the Services following publication of updated Terms constitutes acceptance of the revised Terms.</p>
                <p>Research Spectrum may additionally notify users by email regarding material changes.</p>
              </div>
            </div>
            {/* 20 */}
            <div className="policy-section" id="ts-20">
              <div className="ps-head"><div className="ps-num">20</div><div className="ps-title">Force Majeure</div></div>
              <div className="ps-body">
                <p>
                  Research Spectrum shall not be liable for delays, interruptions, failures, or inability to provide Services resulting from events beyond its reasonable control, including but not limited to:
                </p>
                <ul>
                  <li>Natural disasters</li>
                  <li>Internet outages</li>
                  <li>Cyberattacks</li>
                  <li>Government actions</li>
                  <li>Armed conflicts</li>
                  <li>Labor disputes</li>
                  <li>Infrastructure failures</li>
                </ul>
              </div>
            </div>
            {/* 21 */}
            <div className="policy-section" id="ts-21">
              <div className="ps-head"><div className="ps-num">21</div><div className="ps-title">Governing Law</div></div>
              <div className="ps-body">
                <p>These Terms shall be governed by and construed in accordance with the laws of the Hashemite Kingdom of Jordan.</p>
                <p>Any disputes arising from or relating to these Terms shall be subject to the applicable laws and courts of Jordan.</p>
              </div>
            </div>
            {/* 22 */}
            <div className="policy-section" id="ts-22">
              <div className="ps-head"><div className="ps-num">22</div><div className="ps-title">Language</div></div>
              <div className="ps-body">
                <p>These Terms may be provided in multiple languages.</p>
                <p>In the event of any discrepancy, inconsistency, conflict, or ambiguity between language versions, the English version shall prevail.</p>
              </div>
            </div>
            {/* 23 */}
            <div className="policy-section" id="ts-23">
              <div className="ps-head"><div className="ps-num">23</div><div className="ps-title">Contact</div></div>
              <div className="ps-body">
                <p>For questions regarding these Terms, please contact:</p>
                <div className="ps-contact-card">
                  <div className="ps-cc-ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  </div>
                  <div>
                    <div className="ps-cc-label">Terms Contact</div>
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
