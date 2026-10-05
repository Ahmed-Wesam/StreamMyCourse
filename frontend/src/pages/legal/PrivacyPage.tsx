import { useRef } from 'react'
import { Link } from 'react-router-dom'

import { usePageTitle } from '../../lib/page-title'
import { usePolicySidebar } from './usePolicySidebar'
import './PrivacyPage.css'

export default function PrivacyPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  usePageTitle("Privacy Policy")
  usePolicySidebar(rootRef)

  return (
    <div ref={rootRef} className="pg-privacy text-rs-ink">
      <section className="pp-hero">
        <div className="wrap">
          <div className="eyebrow"><span className="dot" />Privacy Policy</div>
          <h1 style={{ marginTop: "16px" }}>Research Spectrum<br />Privacy Policy</h1>
          <p className="sub">Learn how Research Spectrum collects, uses, stores, protects, and processes information when you access or use our educational platform and services.</p>
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
              Data Protection
            </span>
          </div>
          <div className="legal-notice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>
              This Privacy Policy governs the use of Research Spectrum services and should be reviewed periodically for updates. Continued use of the Services after publication of an updated Privacy Policy constitutes acceptance of the revised policy.
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
              <button className="sidebar-link" data-target="pp-intro" type="button"><span className="sl-num">—</span>Introduction</button>
              <button className="sidebar-link" data-target="pp-1" type="button"><span className="sl-num">1.</span>Information We Collect</button>
              <button className="sidebar-link" data-target="pp-2" type="button"><span className="sl-num">2.</span>How We Use Information</button>
              <button className="sidebar-link" data-target="pp-3" type="button"><span className="sl-num">3.</span>Marketing Communications</button>
              <button className="sidebar-link" data-target="pp-4" type="button"><span className="sl-num">4.</span>Device &amp; Access Monitoring</button>
              <button className="sidebar-link" data-target="pp-5" type="button"><span className="sl-num">5.</span>Sharing of Information</button>
              <button className="sidebar-link" data-target="pp-6" type="button"><span className="sl-num">6.</span>Payment Information</button>
              <button className="sidebar-link" data-target="pp-7" type="button"><span className="sl-num">7.</span>Certificate Verification</button>
              <button className="sidebar-link" data-target="pp-8" type="button"><span className="sl-num">8.</span>Reviews, Testimonials &amp; Feedback</button>
              <button className="sidebar-link" data-target="pp-9" type="button"><span className="sl-num">9.</span>Data Retention</button>
              <button className="sidebar-link" data-target="pp-10" type="button"><span className="sl-num">10.</span>Data Security</button>
              <button className="sidebar-link" data-target="pp-11" type="button"><span className="sl-num">11.</span>International Users</button>
              <button className="sidebar-link" data-target="pp-12" type="button"><span className="sl-num">12.</span>Children's Privacy</button>
              <button className="sidebar-link" data-target="pp-13" type="button"><span className="sl-num">13.</span>Your Rights</button>
              <button className="sidebar-link" data-target="pp-14" type="button"><span className="sl-num">14.</span>Changes to This Policy</button>
              <button className="sidebar-link" data-target="pp-15" type="button"><span className="sl-num">15.</span>Language</button>
              <button className="sidebar-link" data-target="pp-16" type="button"><span className="sl-num">16.</span>Contact</button>
            </nav>
          </div>
        </aside>
        {/* CONTENT */}
        <div className="policy-main">
          <div className="policy-content">
            {/* Introduction */}
            <div className="policy-intro-section" id="pp-intro" style={{ scrollMarginTop: "110px" }}>
              <div className="pi-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                Privacy Policy
              </div>
              <div className="ps-body">
                <p>Research Spectrum ("Research Spectrum", "we", "our", or "us") respects your privacy and is committed to protecting your personal information.</p>
                <p>
                  This Privacy Policy explains how we collect, use, store, disclose, and protect information when you access or use our website, educational platform, courses, assessments, certifications, digital resources, and related services (collectively, the "Services").
                </p>
                <p>By accessing or using our Services, you agree to the collection and use of information in accordance with this Privacy Policy.</p>
              </div>
              <div className="pi-operator">
                <b>Operator:</b>
                Research Spectrum is operated by Bahaa Aburayya for Electronic Shopping, a sole proprietorship registered in the Hashemite Kingdom of Jordan.
              </div>
            </div>
            {/* Section 1 */}
            <div className="policy-section" id="pp-1">
              <div className="ps-head"><div className="ps-num">1</div><div className="ps-title">Information We Collect</div></div>
              <div className="ps-body">
                <h4>Information You Provide</h4>
                <p>We may collect information that you voluntarily provide, including:</p>
                <ul>
                  <li>Full name</li>
                  <li>Email address</li>
                  <li>Country of residence</li>
                  <li>Profession</li>
                  <li>Institution and related profile details</li>
                  <li>Account credentials</li>
                  <li>Billing information</li>
                  <li>Payment-related information</li>
                  <li>Research Team application details and application PII (such as name, email, country, institution, position, research areas, interests, motivation, and related responses)</li>
                  <li>Support requests</li>
                  <li>Feedback</li>
                  <li>Reviews and testimonials</li>
                  <li>Communications with Research Spectrum</li>
                </ul>
                <h4>Educational Information</h4>
                <p>We may collect information relating to your use of educational services, including:</p>
                <ul>
                  <li>Course enrollments</li>
                  <li>Private lesson notes</li>
                  <li>Assignment submissions and related evaluator feedback</li>
                  <li>Lesson completion status</li>
                  <li>Assessment results</li>
                  <li>Quiz results</li>
                  <li>Certification status</li>
                  <li>Learning progress</li>
                  <li>Course activity history</li>
                </ul>
                <h4>Technical Information</h4>
                <p>We may automatically collect technical information, including:</p>
                <ul>
                  <li>IP address</li>
                  <li>Browser type and version</li>
                  <li>Operating system</li>
                  <li>Device type</li>
                  <li>Device identifiers</li>
                  <li>Login history</li>
                  <li>Session information</li>
                  <li>Network information</li>
                  <li>Platform activity logs</li>
                  <li>Security-related information</li>
                  <li>Error reports</li>
                  <li>Usage analytics</li>
                </ul>
                <h4>Cookies and Similar Technologies</h4>
                <p>We may use:</p>
                <ul><li>Cookies</li><li>Local storage technologies</li><li>Session identifiers</li><li>Analytics tools</li><li>Security technologies</li></ul>
                <p>to improve functionality, security, performance, and user experience.</p>
              </div>
            </div>
            {/* Section 2 */}
            <div className="policy-section" id="pp-2">
              <div className="ps-head"><div className="ps-num">2</div><div className="ps-title">How We Use Information</div></div>
              <div className="ps-body">
                <p>We may use information to:</p>
                <ul>
                  <li>Provide Services</li>
                  <li>Process purchases</li>
                  <li>Deliver educational content</li>
                  <li>Manage user accounts</li>
                  <li>Verify course access</li>
                  <li>Enforce device limitations</li>
                  <li>Enforce licensing restrictions</li>
                  <li>Prevent fraud</li>
                  <li>Detect unauthorized account sharing</li>
                  <li>Protect intellectual property</li>
                  <li>Improve educational content</li>
                  <li>Analyze platform performance</li>
                  <li>Respond to support requests</li>
                  <li>Generate certificates</li>
                  <li>Verify certificate authenticity</li>
                  <li>Comply with legal obligations</li>
                  <li>Communicate with users</li>
                </ul>
              </div>
            </div>
            {/* Section 3 */}
            <div className="policy-section" id="pp-3">
              <div className="ps-head"><div className="ps-num">3</div><div className="ps-title">Marketing Communications</div></div>
              <div className="ps-body">
                <p>Research Spectrum may send:</p>
                <ul>
                  <li>Newsletters</li>
                  <li>Educational updates</li>
                  <li>Product announcements</li>
                  <li>Promotional offers</li>
                  <li>Course launch announcements</li>
                  <li>Marketing communications</li>
                </ul>
                <p>
                  There is no in-app marketing-preference or unsubscribe control today. To request that marketing emails stop, contact support using the Contact page or the email address listed in the Contact section below.
                </p>
                <p>Even if marketing communications are disabled, Research Spectrum may continue sending:</p>
                <ul>
                  <li>Account notices</li>
                  <li>Security notifications</li>
                  <li>Password reset emails</li>
                  <li>Transaction confirmations</li>
                  <li>Certificate notifications</li>
                  <li>Service announcements</li>
                  <li>Legal notices</li>
                </ul>
              </div>
            </div>
            {/* Section 4 */}
            <div className="policy-section" id="pp-4">
              <div className="ps-head"><div className="ps-num">4</div><div className="ps-title">Device and Access Monitoring</div></div>
              <div className="ps-body">
                <p>To protect educational content and enforce licensing restrictions, Research Spectrum may monitor:</p>
                <ul><li>Device registrations</li><li>Login activity</li><li>Session activity</li><li>Access patterns</li><li>Security events</li><li>Technical identifiers</li></ul>
                <p>Research Spectrum may use technical measures to enforce:</p>
                <ul><li>Single-session access restrictions</li><li>Anti-piracy protections</li><li>Security controls</li></ul>
              </div>
            </div>
            {/* Section 5 */}
            <div className="policy-section" id="pp-5">
              <div className="ps-head"><div className="ps-num">5</div><div className="ps-title">Sharing of Information</div></div>
              <div className="ps-body">
                <p>Research Spectrum does not sell personal information.</p>
                <p>We may share information with:</p>
                <h4>Service Providers</h4>
                <p>Including providers of:</p>
                <ul><li>Hosting services</li><li>Analytics services</li><li>Email services</li><li>Security services</li><li>Payment processing services</li><li>Video delivery services</li></ul>
                <h4>Legal Requirements</h4>
                <p>We may disclose information where required to:</p>
                <ul>
                  <li>Comply with laws</li>
                  <li>Respond to court orders</li>
                  <li>Respond to lawful government requests</li>
                  <li>Protect legal rights</li>
                  <li>Prevent fraud</li>
                  <li>Enforce our Terms &amp; Conditions</li>
                </ul>
                <h4>Business Protection</h4>
                <p>Information may be disclosed where reasonably necessary to:</p>
                <ul>
                  <li>Protect intellectual property</li>
                  <li>Investigate abuse</li>
                  <li>Investigate fraud</li>
                  <li>Investigate unauthorized content distribution</li>
                  <li>Protect platform security</li>
                </ul>
              </div>
            </div>
            {/* Section 6 */}
            <div className="policy-section" id="pp-6">
              <div className="ps-head"><div className="ps-num">6</div><div className="ps-title">Payment Information</div></div>
              <div className="ps-body">
                <p>Payments are processed by third-party payment providers.</p>
                <p>Research Spectrum does not store complete payment card information.</p>
                <p>Payment information is handled in accordance with the policies and security standards of the applicable payment processor.</p>
              </div>
            </div>
            {/* Section 7 */}
            <div className="policy-section" id="pp-7">
              <div className="ps-head"><div className="ps-num">7</div><div className="ps-title">Certificate Verification</div></div>
              <div className="ps-body">
                <p>Research Spectrum may maintain records relating to:</p>
                <ul><li>Certificate issuance</li><li>Completion dates</li><li>Assessment outcomes</li><li>Verification identifiers</li><li>Verification identifiers (credential IDs)</li></ul>
                <p>for verification and fraud prevention purposes.</p>
              </div>
            </div>
            {/* Section 8 */}
            <div className="policy-section" id="pp-8">
              <div className="ps-head"><div className="ps-num">8</div><div className="ps-title">Reviews, Testimonials, and Feedback</div></div>
              <div className="ps-body">
                <p>By submitting reviews, testimonials, feedback, comments, or similar content, you grant Research Spectrum permission to:</p>
                <ul>
                  <li>Display such content</li>
                  <li>Publish such content</li>
                  <li>Reproduce such content</li>
                  <li>Use such content for educational purposes</li>
                  <li>Use such content for promotional purposes</li>
                </ul>
                <p>Research Spectrum may edit content for formatting, clarity, or length.</p>
              </div>
            </div>
            {/* Section 9 */}
            <div className="policy-section" id="pp-9">
              <div className="ps-head"><div className="ps-num">9</div><div className="ps-title">Data Retention</div></div>
              <div className="ps-body">
                <p>Research Spectrum may retain information for as long as reasonably necessary to:</p>
                <ul>
                  <li>Provide Services</li>
                  <li>Maintain records</li>
                  <li>Verify certifications</li>
                  <li>Resolve disputes</li>
                  <li>Enforce agreements</li>
                  <li>Comply with legal obligations</li>
                  <li>Protect intellectual property</li>
                </ul>
                <p>Certain information may be retained even after account closure where legally permitted or required.</p>
                <h4>Educational and Certification Records</h4>
                <p>
                  Research Spectrum stores educational records including course completion records, quiz results, assignment outcomes, certificate records, and credential verification records. Certain certification, completion, credential verification, and fraud-prevention records may be retained after account closure where reasonably necessary to support certificate verification, dispute resolution, legal compliance, platform security, or fraud prevention.
                </p>
              </div>
            </div>
            {/* Section 10 */}
            <div className="policy-section" id="pp-10">
              <div className="ps-head"><div className="ps-num">10</div><div className="ps-title">Data Security</div></div>
              <div className="ps-body">
                <p>Research Spectrum implements reasonable administrative, technical, and organizational safeguards designed to protect information from:</p>
                <ul><li>Unauthorized access</li><li>Unauthorized disclosure</li><li>Misuse</li><li>Alteration</li><li>Destruction</li></ul>
                <p>However, no method of transmission or storage is completely secure, and Research Spectrum cannot guarantee absolute security.</p>
              </div>
            </div>
            {/* Section 11 */}
            <div className="policy-section" id="pp-11">
              <div className="ps-head"><div className="ps-num">11</div><div className="ps-title">International Users</div></div>
              <div className="ps-body">
                <p>Users accessing Research Spectrum from outside Jordan acknowledge that information may be processed and stored in jurisdictions different from their own.</p>
                <p>By using the Services, you consent to such transfers where permitted by applicable law.</p>
              </div>
            </div>
            {/* Section 12 */}
            <div className="policy-section" id="pp-12">
              <div className="ps-head"><div className="ps-num">12</div><div className="ps-title">Children's Privacy</div></div>
              <div className="ps-body">
                <p>Research Spectrum is not intended for individuals under eighteen (18) years of age.</p>
                <p>We do not knowingly collect personal information from children.</p>
                <p>If we become aware that personal information from a child has been collected, we may delete such information.</p>
              </div>
            </div>
            {/* Section 13 */}
            <div className="policy-section" id="pp-13">
              <div className="ps-head"><div className="ps-num">13</div><div className="ps-title">Your Rights</div></div>
              <div className="ps-body">
                <p>Subject to applicable law, users may request:</p>
                <ul>
                  <li>Access to personal information</li>
                  <li>Correction of inaccurate information</li>
                  <li>Deletion of certain information</li>
                  <li>Restriction of processing</li>
                  <li>Withdrawal of consent where applicable</li>
                </ul>
                <p>
                  The platform does not currently offer separate privacy preference controls for certificate public visibility or profile sharing toggles. Certificate verification records may still be retained and used as described in Certificate Verification and Data Retention.
                </p>
                <h4>Account Deletion</h4>
                <p>
                  There is no in-app account deletion control today. To request account deletion, contact support using the Contact page or the email address listed in the Contact section below. Certain educational, certification, purchase, Research Team application, and fraud-prevention records may be retained after account deletion as described in Data Retention.
                </p>
                <p>Research Spectrum may decline requests where permitted or required by law.</p>
              </div>
            </div>
            {/* Section 14 */}
            <div className="policy-section" id="pp-14">
              <div className="ps-head"><div className="ps-num">14</div><div className="ps-title">Changes to This Privacy Policy</div></div>
              <div className="ps-body">
                <p>Research Spectrum may modify this Privacy Policy at any time.</p>
                <p>Updated versions will be published on the website.</p>
                <p>Continued use of the Services after publication of an updated Privacy Policy constitutes acceptance of the revised policy.</p>
                <p>Research Spectrum may additionally notify users of significant changes via email.</p>
              </div>
            </div>
            {/* Section 15 */}
            <div className="policy-section" id="pp-15">
              <div className="ps-head"><div className="ps-num">15</div><div className="ps-title">Language</div></div>
              <div className="ps-body">
                <p>This Privacy Policy may be provided in multiple languages.</p>
                <p>In the event of any discrepancy, inconsistency, conflict, or ambiguity between language versions, the English version shall prevail.</p>
              </div>
            </div>
            {/* Section 16 */}
            <div className="policy-section" id="pp-16">
              <div className="ps-head"><div className="ps-num">16</div><div className="ps-title">Contact</div></div>
              <div className="ps-body">
                <p>For privacy-related inquiries, requests, or concerns, please contact:</p>
                <div className="ps-contact-card">
                  <div className="ps-cc-ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  </div>
                  <div className="ps-cc-body">
                    <div className="ps-cc-label">Privacy Contact</div>
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
