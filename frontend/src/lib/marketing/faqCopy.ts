/** Static FAQ marketing copy (no JSX). Prototype text for RS-2 Slice D2. */

export type FaqItem = {
  id: string
  question: string
  answer: string
}

type FaqCategory = {
  id: string
  /** DOM id for category jump links (`#cat-…`). */
  anchor: string
  title: string
  tag?: string
  items: readonly FaqItem[]
}

export const faqHero = {
  eyebrow: "Research Spectrum Guidance Center",
  titleLine1: "Questions About",
  titleHighlight: "Learning Research?",
  sub: "Answers about courses, certificates, assessments, and Research Team eligibility — everything you need to navigate your Research Spectrum journey with confidence.",
  trustItems: [
    "Course & Certificate Guidance",
    "Research Team Eligibility",
    "Quiz & Assignment Support",
    "Verified Credentials",
  ] as const,
  primaryCta: "Explore Courses",
  contactCta: "Contact Support",
  supportCard: {
    title: "Research Spectrum Support",
    rows: [
      { label: "Average Response Time", value: "1–2 Business Days", pill: true },
      { label: "Research Team Guidance", value: "Included" },
      { label: "Student Support", value: "Personally Reviewed" },
    ],
  },
} as const

export const faqStillNeedHelp = {
  title: "Still Need Help?",
  body: "If you can't find what you're looking for here, reach out and we'll help. Our team personally reviews every support request and responds within 1–2 business days.",
  primaryCta: "Contact Support",
  secondaryCta: "Explore Courses",
} as const

export const faqCategories: readonly FaqCategory[] = [
  {
    id: "getting-started",
    anchor: "cat-getting-started",
    title: "Getting Started",
    tag: "Start Here",
    items: [
      {
        id: "getting-started-what-is-research-spectrum",
        question: "What is Research Spectrum?",
        answer: "Research Spectrum is a structured online research education platform designed specifically for healthcare professionals. It provides four comprehensive courses covering Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis. Each course includes expert-led video lectures, module quizzes, a graded final assignment, and a competency-based certificate. The platform also features a Research Team pathway for students who complete all four courses.",
      },
      {
        id: "getting-started-who-are-the-courses-designed-for",
        question: "Who are the courses designed for?",
        answer: "Research Spectrum is designed for healthcare professionals who want to develop practical research skills — including medical students, residents, fellows, physicians, nurses, pharmacists, allied health professionals, academic researchers, and public health professionals. No prior research experience is required for any course.",
      },
      {
        id: "getting-started-do-i-need-prior-research-experience",
        question: "Do I need prior research experience?",
        answer: "No prior research experience is required. Research Spectrum is built to take healthcare professionals from no research background to independently capable researchers. The curriculum is structured progressively — each course builds on the previous one, beginning with foundational research methodology before advancing to statistics, scientific writing, and systematic reviews.",
      },
      {
        id: "getting-started-can-complete-beginners-enroll",
        question: "Can complete beginners enroll?",
        answer: "Yes. Research Spectrum is explicitly designed for beginners. The Research Methodology course — which is the recommended starting point — assumes no prior research knowledge. All key concepts are introduced from the ground up. Students who are completely new to research are actively encouraged to enroll, and the structured pathway is designed to support them through to publication-level competency.",
      },
      {
        id: "getting-started-how-does-learning-work-on-research-spectrum",
        question: "How does learning work on Research Spectrum?",
        answer: "Each course is divided into structured modules containing expert-led video lectures, readings, and practical exercises. After completing each module, students take a knowledge check quiz to confirm understanding before progressing. Upon completing all modules and passing their quizzes, students submit a final assignment which is evaluated by subject-matter experts. Passing the assignment earns a verified certificate. All learning is self-paced — there are no deadlines or cohort schedules.",
      },
      {
        id: "getting-started-how-long-do-courses-take-to-complete",
        question: "How long do courses take to complete?",
        answer: "Each course contains 12–20 hours of video content, plus time for quizzes, the final assignment, and review. Most students who study consistently complete a course over 4–8 weeks. Because all courses are self-paced, you can take longer or shorter depending on your schedule. There is no penalty for taking more time.",
      },
    ],
  },
  {
    id: "courses",
    anchor: "cat-courses",
    title: "Courses",
    tag: "Key Topic",
    items: [
      {
        id: "courses-what-courses-are-available",
        question: "What courses are available?",
        answer: "Research Spectrum currently offers four courses: Research Methodology (study design, ethics, evidence evaluation), Statistics & SPSS (statistical analysis, hypothesis testing, SPSS software), Scientific Writing (manuscript structure, journal submission, reporting guidelines), and Systematic Reviews & Meta-Analysis (PRISMA methodology, evidence synthesis). All four courses can be purchased individually or as a bundle.",
      },
      {
        id: "courses-can-i-purchase-courses-individually-or-must-i-buy-the-bundle",
        question: "Can I purchase courses individually, or must I buy the bundle?",
        answer: "Each course can be purchased individually. The Research Mastery Bundle — which includes all four courses — is also available. Individual course purchases are suitable if you want to focus on a specific topic. The bundle is recommended for students pursuing the full Research Team pathway, as all four certificates are required for eligibility.",
      },
      {
        id: "courses-what-is-included-in-each-course",
        question: "What is included in each course?",
        answer: "Every course includes: 12–20 hours of expert-led video lectures; structured modules with readings and exercises; module knowledge-check quizzes; a graded final assignment evaluated by subject-matter experts with written feedback; downloadable resources including templates, datasets, example submissions, and rubrics; a verified competency-based certificate; progress tracking; and lifetime access for as long as the course remains available.",
      },
      {
        id: "courses-do-courses-include-lifetime-access",
        question: "Do courses include lifetime access?",
        answer: "Yes. All Research Spectrum courses include lifetime access for as long as the course remains available. You can revisit lectures, rewatch modules, review your quiz feedback, and access downloadable resources at any time after purchase — including access to future content updates. There is no subscription fee, and access continues for as long as the course remains available.",
      },
      {
        id: "courses-can-i-access-courses-on-mobile-devices",
        question: "Can I access courses on mobile devices?",
        answer: "Yes. Research Spectrum is accessible from any device with a modern web browser — desktop, tablet, or smartphone. Your progress is saved to your account, so you can begin a session on one device and continue on another without losing your place. For the best experience with SPSS-related content, a desktop or laptop is recommended where software demonstrations are shown. Please note that your account may be registered on up to three (3) devices, with one (1) active session at a time.",
      },
      {
        id: "courses-how-often-are-courses-updated",
        question: "How often are courses updated?",
        answer: "Courses are reviewed and updated periodically to reflect current evidence-based standards, updated reporting guidelines (such as PRISMA, CONSORT), and new SPSS versions. All enrolled students receive access to updates automatically as part of their lifetime access — there is no additional charge for course updates or new content additions.",
      },
    ],
  },
  {
    id: "quizzes-assignments",
    anchor: "cat-quizzes-assignments",
    title: "Quizzes & Assignments",
    items: [
      {
        id: "quizzes-assignments-are-module-quizzes-required",
        question: "Are module quizzes required?",
        answer: "Yes. Module quizzes are a required part of each course. They must be passed before progressing to later modules. Quizzes serve as mastery-based checkpoints — they confirm understanding of the module material before new concepts are introduced. Passing all module quizzes is also a prerequisite for accessing and submitting the final assignment.",
      },
      {
        id: "quizzes-assignments-what-score-is-required-to-pass-quizzes",
        question: "What score is required to pass quizzes?",
        answer: "Module quizzes require a score of 70% or higher to pass, with unlimited retakes and no penalty. The mastery-based approach means you can review the material and retake the quiz as many times as needed until you reach the 70% threshold — the focus is on genuine understanding, not time-pressure performance. The final assignment also requires a rubric score of 70% or higher to pass. Each assignment rubric category is clearly specified in the grading criteria available from the course assignment page.",
      },
      {
        id: "quizzes-assignments-can-i-retake-quizzes-if-i-don-t-pass",
        question: "Can I retake quizzes if I don't pass?",
        answer: "Yes. All quizzes can be retaken an unlimited number of times with no penalty and no waiting period between attempts. Research Spectrum uses mastery learning — the goal is genuine understanding, not time-pressure performance. Review the relevant module content and retake the quiz when you feel ready. There is no limit on attempts, and your best performance is what matters.",
      },
      {
        id: "quizzes-assignments-are-quiz-attempts-limited",
        question: "Are quiz attempts limited?",
        answer: "No. Quiz attempts are unlimited. You may retake any quiz as many times as needed with no restrictions, no time penalties, and no reduction in grade. This approach supports genuine mastery learning — students are encouraged to review material and retake quizzes until they fully understand the content, not just until they achieve a minimum score.",
      },
      {
        id: "quizzes-assignments-how-do-final-assignments-work",
        question: "How do final assignments work?",
        answer: "Each course concludes with a final assignment in which students apply course skills to a real dataset or research scenario. Assignments are submitted through the platform and evaluated by subject-matter evaluators. You receive a rubric-based score and detailed written feedback covering strengths, areas for improvement, and evaluator notes. A score of 70% or higher is required to pass. Passing the assignment triggers automatic certificate issuance.",
      },
      {
        id: "quizzes-assignments-can-assignments-be-resubmitted-if-they-don-t-pass",
        question: "Can assignments be resubmitted if they don't pass?",
        answer: "Yes. Research Spectrum uses mastery-based assignment evaluation. If your submission does not achieve a passing score, you will receive a detailed revision request with written feedback identifying what needs to be improved. You may then revise your work and resubmit. There is no limit on resubmission attempts, and you receive evaluator feedback on every submission. Your revision history is tracked and visible on the assignment page.",
      },
      {
        id: "quizzes-assignments-how-long-does-assignment-grading-take",
        question: "How long does assignment grading take?",
        answer: "Assignments are typically assigned to an evaluator within 24–48 hours of submission. The evaluation itself takes 3–5 business days depending on evaluator availability and submission complexity. You can track the exact stage of your submission — from submitted, through assigned, under review, and feedback ready — using the Evaluator Status tracker on your assignment page.",
      },
      {
        id: "quizzes-assignments-what-happens-if-revisions-are-requested",
        question: "What happens if revisions are requested?",
        answer: "If your assignment receives a revision request, you will be notified and your assignment page will display detailed evaluator feedback — including specific strengths, areas requiring improvement, and written evaluator notes. Review this feedback carefully, revise your submission accordingly, and resubmit through the same assignment portal. Each revision attempt receives the same quality of evaluator feedback as the initial submission.",
      },
    ],
  },
  {
    id: "certificates",
    anchor: "cat-certificates",
    title: "Certificates",
    tag: "Key Topic",
    items: [
      {
        id: "certificates-how-do-i-earn-a-certificate",
        question: "How do I earn a certificate?",
        answer: "To earn a Research Spectrum certificate, you must: (1) complete all course modules and pass all module knowledge-check quizzes, and (2) submit the final assignment and receive a passing evaluation (70% or higher on the rubric). Once both requirements are met, your certificate is issued automatically and becomes immediately available on your Certificates page and Dashboard.",
      },
      {
        id: "certificates-do-all-courses-include-certificates",
        question: "Do all courses include certificates?",
        answer: "Yes. Every Research Spectrum course includes a competency-based certificate issued upon successful completion of all module quizzes and the final assignment. Certificates are awarded for Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis. Each certificate includes a unique credential ID for public verification.",
      },
      {
        id: "certificates-what-does-certificate-eligibility-mean",
        question: "What does \"certificate eligibility\" mean?",
        answer: "\"Certificate Eligible\" means you have completed all module quizzes and are eligible to submit the final assignment. The certificate itself is issued automatically after the assignment is submitted and receives a passing evaluation. So eligibility is the stage just before certificate issuance — it confirms you have completed all prerequisite steps and just need to submit and pass the final assignment.",
      },
      {
        id: "certificates-can-research-spectrum-certificates-be-verified",
        question: "Can Research Spectrum certificates be verified?",
        answer: "Yes. Every Research Spectrum certificate includes a unique credential ID. Employers, universities, research supervisors, or any third party can verify the authenticity and current status of a certificate by entering the credential ID on the Certificate Verification page. Verification is publicly accessible with no login required.",
      },
      {
        id: "certificates-how-does-the-certificate-verification-process-work",
        question: "How does the certificate verification process work?",
        answer: "Visit the Certificate Verification page, enter the credential ID printed on the certificate, and click Verify. The system will confirm whether the certificate is valid, display the certificate holder's name, the course completed, the issue date, and the certificate status. Verification is instant and public — no account is needed.",
      },
      {
        id: "certificates-what-information-appears-on-a-certificate",
        question: "What information appears on a certificate?",
        answer: "Each Research Spectrum certificate displays: the certificate holder's full name, the course completed, the unique credential ID, the issue date, the instructor's name, and the Research Spectrum branding. Certificates also include a verification seal and a reference to the public verification URL. The name printed on the certificate is taken from your account profile — ensure your profile name is correct before completing your course.",
      },
      {
        id: "certificates-can-a-certificate-be-revoked",
        question: "Can a certificate be revoked?",
        answer: "In rare circumstances, Research Spectrum may revoke a certificate if it was issued in error, if assessment integrity concerns are identified, or if the credential holder requests revocation. A revoked certificate will appear as revoked when verified through the Certificate Verification page. Revocation decisions are documented and communicated to the certificate holder directly.",
      },
    ],
  },
  {
    id: "research-team",
    anchor: "cat-research-team",
    title: "Research Team",
    tag: "Key Topic",
    items: [
      {
        id: "research-team-what-is-the-research-team",
        question: "What is the Research Team?",
        answer: "The Research Spectrum Research Team is a selective group of graduates who collaborate on real research projects — including systematic reviews, meta-analyses, observational studies, and other academic publications. Team members contribute based on their demonstrated skills, with the goal of producing peer-reviewed publications. Membership requires completing all four Research Spectrum courses and earning their certificates, followed by a competitive application process.",
      },
      {
        id: "research-team-who-can-apply-for-the-research-team",
        question: "Who can apply for the Research Team?",
        answer: "Students who have earned certificates from all four Research Spectrum courses — Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis — are eligible to apply for the Research Team. Completing the courses makes you eligible to apply; it does not guarantee acceptance. Applications are reviewed competitively based on skills demonstrated across all four certifications.",
      },
      {
        id: "research-team-q3",
        question: "Does completing all courses guarantee acceptance to the Research Team?",
        answer: "No. Completing all four courses and earning their certificates makes you eligible to apply — it does not guarantee acceptance. Applications are reviewed competitively and acceptance depends on the quality of work demonstrated in the assignments, the skills shown across certifications, and current team capacity. Eligible students are strongly encouraged to apply, and all applicants receive a decision with clear reasoning.",
      },
      {
        id: "research-team-how-are-research-team-applicants-selected",
        question: "How are Research Team applicants selected?",
        answer: "Research Team applications are reviewed based on the quality of work demonstrated in final assignments across all four courses, the overall competency profile shown in the certification history, and — for shortlisted applicants — a brief interview to assess interest, availability, and fit with current projects. Details of the selection process are explained on the Research Team page.",
      },
      {
        id: "research-team-what-types-of-research-projects-are-available",
        question: "What types of research projects are available?",
        answer: "Research Team projects typically include systematic reviews and meta-analyses, narrative reviews, observational studies, and methodological papers. Projects are assigned based on team members' skills, interests, and available capacity. The types of projects vary over time depending on what is actively in progress. Accepted team members are matched to projects that fit their competencies.",
      },
      {
        id: "research-team-can-international-students-apply-for-the-research-team",
        question: "Can international students apply for the Research Team?",
        answer: "Yes. Research Spectrum serves learners internationally and the Research Team is open to eligible students regardless of geographic location. Research collaboration is conducted online, and team members participate remotely. All communication and project work is conducted in English, with Arabic support also available.",
      },
      {
        id: "research-team-q7",
        question: "Can Research Team members receive authorship on published papers?",
        answer: "Yes. Authorship is possible and is assigned based on contribution, following ICMJE authorship criteria. Team members who make substantial intellectual contributions to conception, design, data analysis, or drafting of a manuscript may be included as authors. Authorship decisions are made transparently and communicated to all contributors at the appropriate stage of the project.",
      },
    ],
  },
  {
    id: "purchases",
    anchor: "cat-purchases",
    title: "Purchases & Payments",
    items: [
      {
        id: "purchases-do-i-need-an-account-before-purchasing",
        question: "Do I need an account before purchasing?",
        answer: "Yes. Sign in with your Research Spectrum account before checkout so your purchase is linked to the same profile you use for lessons and progress. After payment is confirmed, access appears on that account—create an account first if you are new, then complete checkout while signed in.",
      },
      {
        id: "purchases-what-payment-methods-are-supported",
        question: "What payment methods are supported?",
        answer: "Research Spectrum accepts Credit and Debit cards (Visa, Mastercard, American Express) as well as regional payment gateways including PayTabs and HyperPay. Additional payment methods may be available over time. All transactions are processed through secure, encrypted payment channels.",
      },
      {
        id: "purchases-can-i-upgrade-from-an-individual-course-to-the-bundle",
        question: "Can I upgrade from an individual course to the bundle?",
        answer: "Yes. If you purchase an individual course and later wish to access the full curriculum, you can purchase additional courses at any time. Contact Research Spectrum support through the Contact page if you'd like to discuss upgrade pricing based on your existing purchases. Additional courses purchased will be added to your account alongside your existing access.",
      },
      {
        id: "purchases-are-payments-secure",
        question: "Are payments secure?",
        answer: "Yes. All payments are processed through secure, encrypted payment gateways. Research Spectrum does not store payment card details on its servers. Transactions are protected by industry-standard security protocols. You will receive an order confirmation and reference number by email immediately after a successful purchase.",
      },
      {
        id: "purchases-can-institutions-purchase-access-for-multiple-students",
        question: "Can institutions purchase access for multiple students?",
        answer: "Yes. Institutional enrollment options are available for hospitals, universities, medical schools, and research institutions. Contact Research Spectrum through the Contact page to discuss group access, institutional pricing, and partnership arrangements. Bulk enrollments are managed through a dedicated process separate from individual checkout.",
      },
      {
        id: "purchases-how-do-refunds-work",
        question: "How do refunds work?",
        answer: "Refund requests should be submitted via the contact form using the \"Billing Question\" category. Include your course name, purchase date, order reference number, and the reason for the refund request. Eligibility is governed by the Research Spectrum Refund Policy. Requests are reviewed and processed by the support team.",
      },
    ],
  },
  {
    id: "account",
    anchor: "cat-account",
    title: "Account & Settings",
    items: [
      {
        id: "account-how-do-i-update-my-profile-information",
        question: "How do I update my profile information?",
        answer: "Profile information — including your name, institution, profession, and research interests — can be updated from the Account page in your dashboard. Changes to your name are reflected across your account and on future certificate documents. If your name has already been printed on an issued certificate and needs correcting, contact support.",
      },
      {
        id: "account-can-i-change-my-email-address",
        question: "Can I change my email address?",
        answer: "Email address changes can be initiated from the Account page. For security, email changes require confirmation from your current address. If you no longer have access to your registered email and need to update it, contact the Research Spectrum support team through the Contact page with verification of your identity.",
      },
      {
        id: "account-how-do-notification-settings-work",
        question: "How do notification settings work?",
        answer: "Notification preferences are managed from the Settings page. You can control notifications for assignment feedback, certificate issuance, Research Team updates, and platform announcements. Settings are saved per account and apply across all devices where you are signed in.",
      },
      {
        id: "account-can-i-manage-my-privacy-settings",
        question: "Can I manage my privacy settings?",
        answer: "Yes. Privacy settings are available from the Settings page. You can control profile visibility, certificate sharing preferences, and data usage settings. Research Spectrum's full privacy practices are detailed in the Privacy Policy.",
      },
      {
        id: "account-how-do-i-reset-my-password",
        question: "How do I reset my password?",
        answer: "Click the \"Forgot password?\" link on the Sign In page. Enter your registered email address and password reset instructions will be sent. If you do not receive the email within a few minutes, check your spam or junk folder. Reset links expire after 24 hours for security. If you continue to have difficulty, contact the support team.",
      },
      {
        id: "account-how-does-certificate-visibility-work-in-my-account",
        question: "How does certificate visibility work in my account?",
        answer: "All earned certificates are accessible from your Certificates page and your Dashboard. Each certificate displays the course name, credential ID, issue date, and a verification link. You can share the verification link with employers, academic institutions, or research supervisors so they can independently confirm its authenticity through the public verification system.",
      },
    ],
  },
  {
    id: "support",
    anchor: "cat-support",
    title: "Support",
    items: [
      {
        id: "support-how-do-i-contact-research-spectrum-support",
        question: "How do I contact Research Spectrum support?",
        answer: "You can contact Research Spectrum through the Contact page using the contact form, by emailing support@researchspectrum.org directly, or through the official Instagram account @researchspectrum. The team responds within 1–2 business days.",
      },
      {
        id: "support-what-is-the-support-response-time",
        question: "What is the support response time?",
        answer: "The Research Spectrum support team aims to respond to all enquiries within 1–2 business days. More complex issues — such as certificate errors, payment disputes, or technical investigations — may require additional time. When you submit a contact form, you will receive a reference number immediately that can be used to track your request.",
      },
      {
        id: "support-can-i-contact-research-spectrum-through-instagram",
        question: "Can I contact Research Spectrum through Instagram?",
        answer: "Yes. The official Research Spectrum Instagram account is @researchspectrum and can be used for general enquiries and platform updates. For course-specific support, assignment questions, certificate issues, or technical problems, please use email or the contact form to ensure your request is properly tracked and responded to.",
      },
      {
        id: "support-is-whatsapp-support-available",
        question: "Is WhatsApp support available?",
        answer: "WhatsApp support is currently being prepared and is not yet live. Until the channel is available, please contact the team via email at support@researchspectrum.org or through the contact form. You can find updates about WhatsApp availability on the Contact page.",
      },
      {
        id: "support-how-do-i-report-a-technical-issue",
        question: "How do I report a technical issue?",
        answer: "Report technical issues through the Contact page using the \"Technical Issue\" category. Include your device type, browser and version, the steps that led to the issue, the exact error message if one appears, and a screenshot if possible. The more detail you provide, the faster the technical team can investigate and resolve the problem.",
      },
      {
        id: "support-where-can-i-verify-a-research-spectrum-certificate",
        question: "Where can I verify a Research Spectrum certificate?",
        answer: "Certificate verification is available at the Certificate Verification page. Enter the credential ID printed on the certificate document and the system will instantly confirm whether the certificate is genuine, display the certificate holder's name, the course, the issue date, and the current status. Verification requires no login and is publicly accessible.",
      },
    ],
  },
]

