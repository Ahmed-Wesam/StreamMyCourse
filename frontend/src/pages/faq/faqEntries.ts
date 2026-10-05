/** FAQ accordion copy ported from FAQ.html. Product-correct answers replace prototype claims the page tests forbid. */

export type FaqPart =
  | string
  | { strong: string }
  | { href: string; label: string; external?: boolean; blank?: boolean }

export type FaqEntry = {
  id: string
  dataQ: string
  question: string
  plain: string
  parts: FaqPart[]
}

export const faqEntries: FaqEntry[] = [
  {
    id: "faq-q-1",
    dataQ: "What is Research Spectrum? Research Spectrum is a structured online research education platform designed specifically for healthcare professionals. It provides four comprehensive courses covering research methodology, statistics and SPSS, scientific writing, and systematic reviews and meta-analysis.",
    question: "What is Research Spectrum?",
    plain: "Research Spectrum is a structured online research education platform designed specifically for healthcare professionals. It provides four comprehensive courses covering Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis. Each course includes expert-led video lectures, module quizzes, a graded final assignment, and a competency-based certificate. The platform also features a Research Team pathway for students who complete all four courses.",
    parts: [
        "Research Spectrum is a structured online research education platform designed specifically for healthcare professionals. It provides four comprehensive courses covering Research Methodology, Statistics & SPSS, Scientific Writing, and Systematic Reviews & Meta-Analysis. Each course includes expert-led video lectures, module quizzes, a graded final assignment, and a competency-based certificate. The platform also features a Research Team pathway for students who complete all four courses.",
    ],
  },
  {
    id: "faq-q-2",
    dataQ: "Who are the courses designed for? Research Spectrum is designed for medical students residents fellows physicians healthcare professionals nurses pharmacists academic researchers and public health professionals.",
    question: "Who are the courses designed for?",
    plain: "Research Spectrum is designed for healthcare professionals who want to develop practical research skills — including medical students, residents, fellows, physicians, nurses, pharmacists, allied health professionals, academic researchers, and public health professionals. No prior research experience is required for any course.",
    parts: [
        "Research Spectrum is designed for healthcare professionals who want to develop practical research skills — including medical students, residents, fellows, physicians, nurses, pharmacists, allied health professionals, academic researchers, and public health professionals. No prior research experience is required for any course.",
    ],
  },
  {
    id: "faq-q-3",
    dataQ: "Do I need prior research experience? No prior research experience is required. Research Spectrum is built for beginners and experienced researchers alike.",
    question: "Do I need prior research experience?",
    plain: "No prior research experience is required. Research Spectrum is built to take healthcare professionals from no research background to independently capable researchers. The curriculum is structured progressively — each course builds on the previous one, beginning with foundational research methodology before advancing to statistics, scientific writing, and systematic reviews.",
    parts: [
        "No prior research experience is required. Research Spectrum is built to take healthcare professionals from no research background to independently capable researchers. The curriculum is structured progressively — each course builds on the previous one, beginning with foundational research methodology before advancing to statistics, scientific writing, and systematic reviews.",
    ],
  },
  {
    id: "faq-q-4",
    dataQ: "Can complete beginners enroll? Yes beginners are welcome and the curriculum starts from foundational concepts.",
    question: "Can complete beginners enroll?",
    plain: "Yes. Research Spectrum is explicitly designed for beginners. The Research Methodology course — which is the recommended starting point — assumes no prior research knowledge. All key concepts are introduced from the ground up. Students who are completely new to research are actively encouraged to enroll, and the structured pathway is designed to support them through to publication-level competency.",
    parts: [
        "Yes. Research Spectrum is explicitly designed for beginners. The Research Methodology course — which is the recommended starting point — assumes no prior research knowledge. All key concepts are introduced from the ground up. Students who are completely new to research are actively encouraged to enroll, and the structured pathway is designed to support them through to publication-level competency.",
    ],
  },
  {
    id: "faq-q-5",
    dataQ: "How does learning work on Research Spectrum? Learning is self-paced through video lectures modules quizzes and assignments.",
    question: "How does learning work on Research Spectrum?",
    plain: "Each course is divided into structured modules containing expert-led video lectures, readings, and practical exercises. After completing each module, students take a knowledge check quiz to confirm understanding before progressing. Upon completing all modules and passing their quizzes, students submit a final assignment which is evaluated by subject-matter experts. Passing the assignment earns a verified certificate. All learning is self-paced — there are no deadlines or cohort schedules.",
    parts: [
        "Each course is divided into structured modules containing expert-led video lectures, readings, and practical exercises. After completing each module, students take a knowledge check quiz to confirm understanding before progressing. Upon completing all modules and passing their quizzes, students submit a final assignment which is evaluated by subject-matter experts. Passing the assignment earns a verified certificate. All learning is self-paced — there are no deadlines or cohort schedules.",
    ],
  },
  {
    id: "faq-q-6",
    dataQ: "How long do courses take to complete? Courses take approximately 20 or more hours of content and most students complete them over several weeks.",
    question: "How long do courses take to complete?",
    plain: "Each course contains 12–20 hours of video content, plus time for quizzes, the final assignment, and review. Most students who study consistently complete a course over 4–8 weeks. Because all courses are self-paced, you can take longer or shorter depending on your schedule. There is no penalty for taking more time.",
    parts: [
        "Each course contains 12–20 hours of video content, plus time for quizzes, the final assignment, and review. Most students who study consistently complete a course over 4–8 weeks. Because all courses are self-paced, you can take longer or shorter depending on your schedule. There is no penalty for taking more time.",
    ],
  },
  {
    id: "faq-q-7",
    dataQ: "What courses are available? Research Methodology Statistics SPSS Scientific Writing Systematic Reviews Meta-Analysis",
    question: "What courses are available?",
    plain: "Research Spectrum currently offers four courses: Research Methodology (study design, ethics, evidence evaluation), Statistics & SPSS (statistical analysis, hypothesis testing, SPSS software), Scientific Writing (manuscript structure, journal submission, reporting guidelines), and Systematic Reviews & Meta-Analysis (PRISMA methodology, evidence synthesis). All four courses can be purchased individually or as a bundle.",
    parts: [
        "Research Spectrum currently offers four courses: ",
        {"strong":"Research Methodology"},
        " (study design, ethics, evidence evaluation), ",
        {"strong":"Statistics & SPSS"},
        " (statistical analysis, hypothesis testing, SPSS software), ",
        {"strong":"Scientific Writing"},
        " (manuscript structure, journal submission, reporting guidelines), and ",
        {"strong":"Systematic Reviews & Meta-Analysis"},
        " (PRISMA methodology, evidence synthesis). All four courses can be purchased individually or as a bundle.",
    ],
  },
  {
    id: "faq-q-8",
    dataQ: "Can I purchase courses individually or must I buy the bundle? You can purchase any individual course or the full bundle.",
    question: "Can I purchase courses individually, or must I buy the bundle?",
    plain: "Each course can be purchased individually. The Research Mastery Bundle — which includes all four courses — is also available. Individual course purchases are suitable if you want to focus on a specific topic. The bundle is recommended if you plan to pursue the full Research Team pathway; see the Research Team page (/research-team) for the live list of admin-required courses and certificates.",
    parts: [
        "Each course can be purchased individually. The Research Mastery Bundle — which includes all four courses — is also available. Individual course purchases are suitable if you want to focus on a specific topic. The bundle is recommended if you plan to pursue the full Research Team pathway; see the Research Team page (/research-team) for the live list of admin-required courses and certificates.",
    ],
  },
  {
    id: "faq-q-9",
    dataQ: "What is included in each course? Courses include video lectures modules quizzes assignments certificates downloadable resources lifetime access.",
    question: "What is included in each course?",
    plain: "Every course includes: 12–20 hours of expert-led video lectures; structured modules with readings and exercises; module knowledge-check quizzes; a graded final assignment evaluated by subject-matter experts with written feedback; downloadable resources including templates, datasets, example submissions, and rubrics; a verified competency-based certificate; progress tracking; and lifetime access for as long as the course remains available.",
    parts: [
        "Every course includes: 12–20 hours of expert-led video lectures; structured modules with readings and exercises; module knowledge-check quizzes; a graded final assignment evaluated by subject-matter experts with written feedback; downloadable resources including templates, datasets, example submissions, and rubrics; a verified competency-based certificate; progress tracking; and lifetime access for as long as the course remains available.",
    ],
  },
  {
    id: "q-lifetime",
    dataQ: "Do courses include lifetime access? Yes all Research Spectrum courses include lifetime access for as long as the course remains available.",
    question: "Do courses include lifetime access?",
    plain: "Yes. All Research Spectrum courses include lifetime access for as long as the course remains available. You can revisit lectures, rewatch modules, review your quiz feedback, and access downloadable resources at any time after purchase — including access to future content updates. There is no subscription fee, and access continues for as long as the course remains available.",
    parts: [
        "Yes. All Research Spectrum courses include lifetime access for as long as the course remains available. You can revisit lectures, rewatch modules, review your quiz feedback, and access downloadable resources at any time after purchase — including access to future content updates. There is no subscription fee, and access continues for as long as the course remains available.",
    ],
  },
  {
    id: "faq-q-10",
    dataQ: "Can I access courses on mobile devices? Yes courses are accessible on desktop tablet and mobile devices. Up to three registered devices with one active session at a time.",
    question: "Can I access courses on mobile devices?",
    plain: "Yes. Research Spectrum is accessible from any device with a modern web browser — desktop, tablet, or smartphone. Your progress is saved to your account, so you can begin a session on one device and continue on another without losing your place. For the best experience with SPSS-related content, a desktop or laptop is recommended where software demonstrations are shown. Please note that your account may be registered on up to three (3) devices, with one (1) active session at a time.",
    parts: [
        "Yes. Research Spectrum is accessible from any device with a modern web browser — desktop, tablet, or smartphone. Your progress is saved to your account, so you can begin a session on one device and continue on another without losing your place. For the best experience with SPSS-related content, a desktop or laptop is recommended where software demonstrations are shown. Please note that your account may be registered on up to three (3) devices, with one (1) active session at a time.",
    ],
  },
  {
    id: "faq-q-11",
    dataQ: "How often are courses updated? Courses are updated regularly to reflect current standards and evidence.",
    question: "How often are courses updated?",
    plain: "Courses are reviewed and updated periodically to reflect current evidence-based standards, updated reporting guidelines (such as PRISMA, CONSORT), and new SPSS versions. All enrolled students receive access to updates automatically as part of their lifetime access — there is no additional charge for course updates or new content additions.",
    parts: [
        "Courses are reviewed and updated periodically to reflect current evidence-based standards, updated reporting guidelines (such as PRISMA, CONSORT), and new SPSS versions. All enrolled students receive access to updates automatically as part of their lifetime access — there is no additional charge for course updates or new content additions.",
    ],
  },
  {
    id: "faq-q-12",
    dataQ: "Are module quizzes required? Yes module quizzes must be passed before accessing later modules and the final assignment.",
    question: "Are module quizzes required?",
    plain: "Yes. Module quizzes are a required part of each course. They must be passed before progressing to later modules. Quizzes serve as mastery-based checkpoints — they confirm understanding of the module material before new concepts are introduced. Passing all module quizzes is also a prerequisite for accessing and submitting the final assignment.",
    parts: [
        "Yes. Module quizzes are a required part of each course. They must be passed before progressing to later modules. Quizzes serve as mastery-based checkpoints — they confirm understanding of the module material before new concepts are introduced. Passing all module quizzes is also a prerequisite for accessing and submitting the final assignment.",
    ],
  },
  {
    id: "q-quiz-pass",
    dataQ: "What score is required to pass quizzes? Module quizzes require a score of 70% or higher to pass.",
    question: "What score is required to pass quizzes?",
    plain: "Module quizzes require a score of 70% or higher to pass, with unlimited retakes and no penalty. The mastery-based approach means you can review the material and retake the quiz as many times as needed until you reach the 70% threshold — the focus is on genuine understanding, not time-pressure performance. The final assignment also requires a rubric score of 70% or higher to pass. Each assignment rubric category is clearly specified in the grading criteria available from the course assignment page.",
    parts: [
        "Module quizzes require a score of 70% or higher to pass, with unlimited retakes and no penalty. The mastery-based approach means you can review the material and retake the quiz as many times as needed until you reach the 70% threshold — the focus is on genuine understanding, not time-pressure performance. The final assignment also requires a rubric score of 70% or higher to pass. Each assignment rubric category is clearly specified in the grading criteria available from the course assignment page.",
    ],
  },
  {
    id: "faq-q-13",
    dataQ: "Can I retake quizzes if I fail? Yes quizzes can be retaken unlimited times with no penalty.",
    question: "Can I retake quizzes if I don't pass?",
    plain: "Yes. All quizzes can be retaken an unlimited number of times with no penalty and no waiting period between attempts. Research Spectrum uses mastery learning — the goal is genuine understanding, not time-pressure performance. Review the relevant module content and retake the quiz when you feel ready. There is no limit on attempts, and your best performance is what matters.",
    parts: [
        "Yes. All quizzes can be retaken an unlimited number of times with no penalty and no waiting period between attempts. Research Spectrum uses mastery learning — the goal is genuine understanding, not time-pressure performance. Review the relevant module content and retake the quiz when you feel ready. There is no limit on attempts, and your best performance is what matters.",
    ],
  },
  {
    id: "faq-q-14",
    dataQ: "Are quiz attempts limited? No quiz attempts are unlimited.",
    question: "Are quiz attempts limited?",
    plain: "No. Quiz attempts are unlimited. You may retake any quiz as many times as needed with no restrictions, no time penalties, and no reduction in grade. This approach supports genuine mastery learning — students are encouraged to review material and retake quizzes until they fully understand the content, not just until they achieve a minimum score.",
    parts: [
        "No. Quiz attempts are unlimited. You may retake any quiz as many times as needed with no restrictions, no time penalties, and no reduction in grade. This approach supports genuine mastery learning — students are encouraged to review material and retake quizzes until they fully understand the content, not just until they achieve a minimum score.",
    ],
  },
  {
    id: "faq-q-15",
    dataQ: "How do final assignments work? Final assignments involve applying course skills to a real dataset or scenario and are evaluated by subject matter experts.",
    question: "How do final assignments work?",
    plain: "Instructors may publish one or more graded assignments on a course (tied to a module). Assignments are submitted through the platform and evaluated by the course owner. You receive a rubric-based score and written feedback. The instructor sets the pass mark. Only published assignments flagged as counting toward a certificate gate certificate issuance — passing an assignment alone does not automatically issue a certificate if other requirements remain.",
    parts: [
        "Instructors may publish one or more graded assignments on a course (tied to a module). Assignments are submitted through the platform and evaluated by the course owner. You receive a rubric-based score and written feedback. The instructor sets the pass mark. Only published assignments flagged as counting toward a certificate gate certificate issuance — passing an assignment alone does not automatically issue a certificate if other requirements remain.",
    ],
  },
  {
    id: "q-asgn-resubmit",
    dataQ: "Can assignments be resubmitted if they do not pass? Yes assignments can be resubmitted after receiving revision feedback.",
    question: "Can assignments be resubmitted if they don't pass?",
    plain: "Yes. Research Spectrum uses mastery-based assignment evaluation. If your submission does not achieve a passing score, you will receive a detailed revision request with written feedback identifying what needs to be improved. You may then revise your work and resubmit. There is no limit on resubmission attempts, and you receive evaluator feedback on every submission. Your revision history is tracked and visible on the assignment page.",
    parts: [
        "Yes. Research Spectrum uses mastery-based assignment evaluation. If your submission does not achieve a passing score, you will receive a detailed revision request with written feedback identifying what needs to be improved. You may then revise your work and resubmit. There is no limit on resubmission attempts, and you receive evaluator feedback on every submission. Your revision history is tracked and visible on the assignment page.",
    ],
  },
  {
    id: "faq-q-16",
    dataQ: "How long does assignment grading take? Assignment grading typically takes 3 to 5 business days.",
    question: "How long does assignment grading take?",
    plain: "Grading turnaround depends on the course owner’s availability. After you submit, the assignment page shows whether your latest attempt is still submitted (awaiting a grade) or graded (with pass/fail and feedback). There is no separate multi-stage evaluator pipeline UI beyond that submission status.",
    parts: [
        "Grading turnaround depends on the course owner’s availability. After you submit, the assignment page shows whether your latest attempt is still submitted (awaiting a grade) or graded (with pass/fail and feedback). There is no separate multi-stage evaluator pipeline UI beyond that submission status.",
    ],
  },
  {
    id: "faq-q-17",
    dataQ: "What happens if revisions are requested for my assignment? You receive detailed feedback and can revise and resubmit.",
    question: "What happens if revisions are requested?",
    plain: "If your assignment receives a revision request, you will be notified and your assignment page will display detailed evaluator feedback — including specific strengths, areas requiring improvement, and written evaluator notes. Review this feedback carefully, revise your submission accordingly, and resubmit through the same assignment portal. Each revision attempt receives the same quality of evaluator feedback as the initial submission.",
    parts: [
        "If your assignment receives a revision request, you will be notified and your assignment page will display detailed evaluator feedback — including specific strengths, areas requiring improvement, and written evaluator notes. Review this feedback carefully, revise your submission accordingly, and resubmit through the same assignment portal. Each revision attempt receives the same quality of evaluator feedback as the initial submission.",
    ],
  },
  {
    id: "q-cert-earn",
    dataQ: "How do I earn a certificate? Pass all module quizzes and the final assignment with 70% or higher.",
    question: "How do I earn a certificate?",
    plain: "To earn a Research Spectrum certificate for a course, you must pass every visible module quiz and pass every published assignment the instructor flagged as counting toward the certificate. Lesson watch progress does not count. If a course has no visible quiz and no published certificate-counting assignment, no certificate is issued. When the requirements are met, your certificate is issued automatically and appears on your Certificates page.",
    parts: [
        "To earn a Research Spectrum certificate for a course, you must pass every visible module quiz and pass every published assignment the instructor flagged as counting toward the certificate. Lesson watch progress does not count. If a course has no visible quiz and no published certificate-counting assignment, no certificate is issued. When the requirements are met, your certificate is issued automatically and appears on your Certificates page.",
    ],
  },
  {
    id: "faq-q-18",
    dataQ: "Do all courses include certificates? Yes every Research Spectrum course includes a competency based certificate.",
    question: "Do all courses include certificates?",
    plain: "Courses can issue a competency-based certificate when their certificate requirements are met (visible module quizzes plus any published certificate-counting assignments). A course with nothing to pass does not issue a certificate. Certificates include a unique credential ID for public verification.",
    parts: [
        "Courses can issue a competency-based certificate when their certificate requirements are met (visible module quizzes plus any published certificate-counting assignments). A course with nothing to pass does not issue a certificate. Certificates include a unique credential ID for public verification.",
    ],
  },
  {
    id: "faq-q-19",
    dataQ: "What does certificate eligibility mean? Certificate eligibility means you have completed all prerequisites and can now submit the final assignment to earn your certificate.",
    question: "What does \"certificate eligibility\" mean?",
    plain: "\"Certificate eligibility\" means you have satisfied the course’s certificate requirements: every visible module quiz passed, and every published certificate-counting assignment passed. The platform does not use a separate pre-issuance eligibility stage or status badge before issuance. When those requirements are met, the certificate is issued automatically.",
    parts: [
        "\"Certificate eligibility\" means you have satisfied the course’s certificate requirements: every visible module quiz passed, and every published certificate-counting assignment passed. The platform does not use a separate pre-issuance eligibility stage or status badge before issuance. When those requirements are met, the certificate is issued automatically.",
    ],
  },
  {
    id: "q-cert-verify",
    dataQ: "Can Research Spectrum certificates be verified? Yes all certificates include a unique credential ID that can be verified publicly.",
    question: "Can Research Spectrum certificates be verified?",
    plain: "Yes. Every Research Spectrum certificate includes a unique credential ID. Employers, universities, research supervisors, or any third party can verify the authenticity and current status of a certificate by entering the credential ID on the Certificate Verification page. Verification is publicly accessible with no login required.",
    parts: [
        "Yes. Every Research Spectrum certificate includes a unique credential ID. Employers, universities, research supervisors, or any third party can verify the authenticity and current status of a certificate by entering the credential ID on the ",
        {"href":"/verify","label":"Certificate Verification page","external":false,"blank":false},
        ". Verification is publicly accessible with no login required.",
    ],
  },
  {
    id: "faq-q-20",
    dataQ: "How does certificate verification work? Enter the credential ID on the certificate verification page to confirm authenticity.",
    question: "How does the certificate verification process work?",
    plain: "Visit the Certificate Verification page, enter the credential ID printed on the certificate, and click Verify. The system will confirm whether the certificate is valid, display the certificate holder's name, the course completed, the issue date, and the certificate status. Verification is instant and public — no account is needed.",
    parts: [
        "Visit the ",
        {"href":"/verify","label":"Certificate Verification page","external":false,"blank":false},
        ", enter the credential ID printed on the certificate, and click Verify. The system will confirm whether the certificate is valid, display the certificate holder's name, the course completed, the issue date, and the certificate status. Verification is instant and public — no account is needed.",
    ],
  },
  {
    id: "faq-q-21",
    dataQ: "What information appears on a Research Spectrum certificate? The certificate shows student name course name credential ID issue date and instructor.",
    question: "What information appears on a certificate?",
    plain: "Each Research Spectrum certificate displays: the certificate holder's full name, the course completed, the unique credential ID, the issue date, the instructor's name, and the Research Spectrum branding. Certificates also include a verification seal and a reference to the public verification URL. The name printed on the certificate is taken from your account profile — ensure your profile name is correct before completing your course.",
    parts: [
        "Each Research Spectrum certificate displays: the certificate holder's full name, the course completed, the unique credential ID, the issue date, the instructor's name, and the Research Spectrum branding. Certificates also include a verification seal and a reference to the public verification URL. The name printed on the certificate is taken from your account profile — ensure your profile name is correct before completing your course.",
    ],
  },
  {
    id: "faq-q-22",
    dataQ: "Can a Research Spectrum certificate be revoked? Yes in rare circumstances certificates may be revoked if issued in error or assessment integrity concerns arise.",
    question: "Can a certificate be revoked?",
    plain: "In rare circumstances, Research Spectrum may revoke a certificate if it was issued in error, if assessment integrity concerns are identified, or if the credential holder requests revocation. A revoked certificate will appear as revoked when verified through the Certificate Verification page. Revocation decisions are documented and communicated to the certificate holder directly.",
    parts: [
        "In rare circumstances, Research Spectrum may revoke a certificate if it was issued in error, if assessment integrity concerns are identified, or if the credential holder requests revocation. A revoked certificate will appear as revoked when verified through the Certificate Verification page. Revocation decisions are documented and communicated to the certificate holder directly.",
    ],
  },
  {
    id: "faq-q-23",
    dataQ: "What is the Research Team? The Research Team is an exclusive group of Research Spectrum graduates who contribute to real published research projects.",
    question: "What is the Research Team?",
    plain: "The Research Spectrum Research Team is a selective group of graduates who collaborate on real research projects — including systematic reviews, meta-analyses, observational studies, and other academic publications. Team members contribute based on their demonstrated skills, with the goal of producing peer-reviewed publications. Membership requires completing all four Research Spectrum courses and earning their certificates, followed by a competitive application process.",
    parts: [
        "The Research Spectrum Research Team is a selective group of graduates who collaborate on real research projects — including systematic reviews, meta-analyses, observational studies, and other academic publications. Team members contribute based on their demonstrated skills, with the goal of producing peer-reviewed publications. Membership requires completing all four Research Spectrum courses and earning their certificates, followed by a competitive application process.",
    ],
  },
  {
    id: "q-rt-apply",
    dataQ: "Who can apply for the Research Team? Students who have completed all four courses and earned all four certificates are eligible to apply.",
    question: "Who can apply for the Research Team?",
    plain: "Students who have earned certificates for the admin-required courses shown on the Research Team page (/research-team) are eligible to apply. Completing those required courses makes you eligible to apply; it does not guarantee acceptance. Applications are reviewed competitively based on skills demonstrated across the required certifications.",
    parts: [
        "Students who have earned certificates for the admin-required courses shown on the Research Team page (/research-team) are eligible to apply. Completing those required courses makes you eligible to apply; it does not guarantee acceptance. Applications are reviewed competitively based on skills demonstrated across the required certifications.",
    ],
  },
  {
    id: "faq-q-24",
    dataQ: "Does completing all courses guarantee Research Team acceptance? No completing courses makes you eligible to apply but acceptance is competitive.",
    question: "Does completing all courses guarantee acceptance to the Research Team?",
    plain: "No. Completing all four courses and earning their certificates makes you eligible to apply — it does not guarantee acceptance. Applications are reviewed competitively and acceptance depends on the quality of work demonstrated in the assignments, the skills shown across certifications, and current team capacity. Eligible students are strongly encouraged to apply, and all applicants receive a decision with clear reasoning.",
    parts: [
        "No. Completing all four courses and earning their certificates makes you eligible to apply — it does not guarantee acceptance. Applications are reviewed competitively and acceptance depends on the quality of work demonstrated in the assignments, the skills shown across certifications, and current team capacity. Eligible students are strongly encouraged to apply, and all applicants receive a decision with clear reasoning.",
    ],
  },
  {
    id: "faq-q-25",
    dataQ: "How are Research Team applicants selected? Applications are reviewed based on assignment performance certificate quality and interview.",
    question: "How are Research Team applicants selected?",
    plain: "Research Team applications are reviewed based on the quality of work demonstrated in final assignments for the required courses, the overall competency profile shown in the certification history, and current team capacity. Details of the selection process are explained on the Research Team page (/research-team).",
    parts: [
        "Research Team applications are reviewed based on the quality of work demonstrated in final assignments for the required courses, the overall competency profile shown in the certification history, and current team capacity. Details of the selection process are explained on the Research Team page (/research-team).",
    ],
  },
  {
    id: "faq-q-26",
    dataQ: "What types of research projects are available through the Research Team? Projects include systematic reviews meta-analyses and observational studies.",
    question: "What types of research projects are available?",
    plain: "Research Team projects typically include systematic reviews and meta-analyses, narrative reviews, observational studies, and methodological papers. Projects are assigned based on team members' skills, interests, and available capacity. The types of projects vary over time depending on what is actively in progress. Accepted team members are matched to projects that fit their competencies.",
    parts: [
        "Research Team projects typically include systematic reviews and meta-analyses, narrative reviews, observational studies, and methodological papers. Projects are assigned based on team members' skills, interests, and available capacity. The types of projects vary over time depending on what is actively in progress. Accepted team members are matched to projects that fit their competencies.",
    ],
  },
  {
    id: "faq-q-27",
    dataQ: "Can international students apply for the Research Team? Yes international students are welcome to apply.",
    question: "Can international students apply for the Research Team?",
    plain: "Yes. Research Spectrum serves learners internationally and the Research Team is open to eligible students regardless of geographic location. Research collaboration is conducted online, and team members participate remotely. All communication and project work is conducted in English, with Arabic support also available.",
    parts: [
        "Yes. Research Spectrum serves learners internationally and the Research Team is open to eligible students regardless of geographic location. Research collaboration is conducted online, and team members participate remotely. All communication and project work is conducted in English, with Arabic support also available.",
    ],
  },
  {
    id: "faq-q-28",
    dataQ: "Can Research Team members receive authorship on published papers? Yes authorship is possible based on contribution.",
    question: "Can Research Team members receive authorship on published papers?",
    plain: "Yes. Authorship is possible and is assigned based on contribution, following ICMJE authorship criteria. Team members who make substantial intellectual contributions to conception, design, data analysis, or drafting of a manuscript may be included as authors. Authorship decisions are made transparently and communicated to all contributors at the appropriate stage of the project.",
    parts: [
        "Yes. Authorship is possible and is assigned based on contribution, following ICMJE authorship criteria. Team members who make substantial intellectual contributions to conception, design, data analysis, or drafting of a manuscript may be included as authors. Authorship decisions are made transparently and communicated to all contributors at the appropriate stage of the project.",
    ],
  },
  {
    id: "faq-q-29",
    dataQ: "Do I need an account before purchasing a course? No you can purchase without an existing account and create one after checkout.",
    question: "Do I need an account before purchasing?",
    plain: "No. You can complete checkout with only your email address. Your course access is linked to that email. After purchase is confirmed, you can either create a new Research Spectrum account or sign in to an existing account — your purchased course access will be applied to your account automatically.",
    parts: [
        "No. You can complete checkout with only your email address. Your course access is linked to that email. After purchase is confirmed, you can either create a new Research Spectrum account or sign in to an existing account — your purchased course access will be applied to your account automatically.",
    ],
  },
  {
    id: "faq-q-30",
    dataQ: "What payment methods are supported? Credit debit card Visa Mastercard HyperPay",
    question: "What payment methods are supported?",
    plain: "Research Spectrum accepts credit and debit cards (Visa, Mastercard) through HyperPay. All transactions are processed through secure, encrypted payment channels and Research Spectrum does not store card details.",
    parts: [
        "Research Spectrum accepts credit and debit cards (Visa, Mastercard) through HyperPay. All transactions are processed through secure, encrypted payment channels and Research Spectrum does not store card details.",
    ],
  },
  {
    id: "faq-q-31",
    dataQ: "Can I upgrade to the bundle after purchasing an individual course? Yes you can upgrade at any time by contacting support.",
    question: "Can I upgrade from an individual course to the bundle?",
    plain: "Yes. If you purchase an individual course and later wish to access the full curriculum, you can purchase additional courses at any time. Contact Research Spectrum support through the Contact page if you'd like to discuss upgrade pricing based on your existing purchases. Additional courses purchased will be added to your account alongside your existing access.",
    parts: [
        "Yes. If you purchase an individual course and later wish to access the full curriculum, you can purchase additional courses at any time. Contact Research Spectrum support through the ",
        {"href":"/contact","label":"Contact page","external":false,"blank":false},
        " if you'd like to discuss upgrade pricing based on your existing purchases. Additional courses purchased will be added to your account alongside your existing access.",
    ],
  },
  {
    id: "faq-q-32",
    dataQ: "Are payments secure? Yes all payments are encrypted and processed through secure payment gateways.",
    question: "Are payments secure?",
    plain: "Yes. All payments are processed through secure, encrypted payment gateways. Research Spectrum does not store payment card details on its servers. Transactions are protected by industry-standard security protocols. You will receive an order confirmation and reference number by email immediately after a successful purchase.",
    parts: [
        "Yes. All payments are processed through secure, encrypted payment gateways. Research Spectrum does not store payment card details on its servers. Transactions are protected by industry-standard security protocols. You will receive an order confirmation and reference number by email immediately after a successful purchase.",
    ],
  },
  {
    id: "faq-q-33",
    dataQ: "Can institutions or hospitals purchase bulk access? Yes institutional and bulk enrollment options are available.",
    question: "Can institutions purchase access for multiple students?",
    plain: "Yes. Institutional enrollment options are available for hospitals, universities, medical schools, and research institutions. Contact Research Spectrum through the Contact page to discuss group access, institutional pricing, and partnership arrangements. Bulk enrollments are managed through a dedicated process separate from individual checkout.",
    parts: [
        "Yes. Institutional enrollment options are available for hospitals, universities, medical schools, and research institutions. Contact Research Spectrum through the ",
        {"href":"/contact","label":"Contact page","external":false,"blank":false},
        " to discuss group access, institutional pricing, and partnership arrangements. Bulk enrollments are managed through a dedicated process separate from individual checkout.",
    ],
  },
  {
    id: "faq-q-34",
    dataQ: "How do refunds work? Refund requests should be submitted through the contact form and are subject to the refund policy.",
    question: "How do refunds work?",
    plain: "Refund requests should be submitted via the contact form using the \"Billing Question\" category. Include your course name, purchase date, order reference number, and the reason for the refund request. Eligibility is governed by the Research Spectrum Refund Policy. Requests are reviewed and processed by the support team.",
    parts: [
        "Refund requests should be submitted via the contact form using the \"Billing Question\" category. Include your course name, purchase date, order reference number, and the reason for the refund request. Eligibility is governed by the Research Spectrum ",
        {"href":"/refund","label":"Refund Policy","external":false,"blank":false},
        ". Requests are reviewed and processed by the support team.",
    ],
  },
  {
    id: "faq-q-35",
    dataQ: "How do I update my profile information name institution profession? Update your profile from the Account page in your dashboard.",
    question: "How do I update my profile information?",
    plain: "Profile information — including your name, institution, profession, and research interests — can be updated from the Account page in your dashboard. Changes to your name are reflected across your account and on future certificate documents. If your name has already been printed on an issued certificate and needs correcting, contact support.",
    parts: [
        "Profile information — including your name, institution, profession, and research interests — can be updated from the ",
        {"href":"/account/profile","label":"Account page","external":false,"blank":false},
        " in your dashboard. Changes to your name are reflected across your account and on future certificate documents. If your name has already been printed on an issued certificate and needs correcting, contact support.",
    ],
  },
  {
    id: "faq-q-36",
    dataQ: "Can I change my email address? Email changes can be made through the Account page or by contacting support.",
    question: "Can I change my email address?",
    plain: "Email address changes can be initiated from the Account page. For security, email changes require confirmation from your current address. If you no longer have access to your registered email and need to update it, contact the Research Spectrum support team through the Contact page with verification of your identity.",
    parts: [
        "Email address changes can be initiated from the Account page. For security, email changes require confirmation from your current address. If you no longer have access to your registered email and need to update it, contact the Research Spectrum support team through the ",
        {"href":"/contact","label":"Contact page","external":false,"blank":false},
        " with verification of your identity.",
    ],
  },
  {
    id: "faq-q-37",
    dataQ: "How do notification settings work? Notification preferences can be managed from the Settings page.",
    question: "How do notification settings work?",
    plain: "Research Spectrum does not offer separate notification preference controls. Assignment feedback, certificate issuance, and important account messages are delivered by email to the address on your Account profile. For help with account email or missing messages, use the Contact page.",
    parts: [
        "Research Spectrum does not offer separate notification preference controls. Assignment feedback, certificate issuance, and important account messages are delivered by email to the address on your Account profile. For help with account email or missing messages, use the Contact page.",
    ],
  },
  {
    id: "faq-q-38",
    dataQ: "Can I manage my privacy settings? Yes privacy preferences are available from the Settings page.",
    question: "Can I manage my privacy settings?",
    plain: "There are no separate privacy preference controls for profile visibility or certificate sharing toggles. You can update your profile details from the Account page. Research Spectrum's full privacy practices — including how we collect and use data — are detailed in the Privacy Policy.",
    parts: [
        "There are no separate privacy preference controls for profile visibility or certificate sharing toggles. You can update your profile details from the Account page. Research Spectrum's full privacy practices — including how we collect and use data — are detailed in the Privacy Policy.",
    ],
  },
  {
    id: "faq-q-39",
    dataQ: "How do I reset my password if I forgot it? Use the Forgot Password link on the login page.",
    question: "How do I reset my password?",
    plain: "Click the \"Forgot password?\" link on the Sign In page. Enter your registered email address and password reset instructions will be sent. If you do not receive the email within a few minutes, check your spam or junk folder. Reset links expire after 24 hours for security. If you continue to have difficulty, contact the support team.",
    parts: [
        "Click the \"Forgot password?\" link on the ",
        {"href":"/login","label":"Sign In page","external":false,"blank":false},
        ". Enter your registered email address and password reset instructions will be sent. If you do not receive the email within a few minutes, check your spam or junk folder. Reset links expire after 24 hours for security. If you continue to have difficulty, contact the support team.",
    ],
  },
  {
    id: "faq-q-40",
    dataQ: "How does certificate visibility work in my account? Certificates are visible on your dashboard and can be shared or downloaded.",
    question: "How does certificate visibility work in my account?",
    plain: "All earned certificates are accessible from your Certificates page and your Dashboard. Each certificate displays the course name, credential ID, issue date, and a verification link. You can share the verification link with employers, academic institutions, or research supervisors so they can independently confirm its authenticity through the public verification system.",
    parts: [
        "All earned certificates are accessible from your ",
        {"href":"/certificates","label":"Certificates page","external":false,"blank":false},
        " and your Dashboard. Each certificate displays the course name, credential ID, issue date, and a verification link. You can share the verification link with employers, academic institutions, or research supervisors so they can independently confirm its authenticity through the public verification system.",
    ],
  },
  {
    id: "faq-q-41",
    dataQ: "How do I contact Research Spectrum support? Via the contact form email or Instagram.",
    question: "How do I contact Research Spectrum support?",
    plain: "You can contact Research Spectrum through the Contact page using the contact form, by emailing support@researchspectrum.org directly, or through the official Instagram account @researchspectrum. The team responds within 1–2 business days.",
    parts: [
        "You can contact Research Spectrum through the ",
        {"href":"/contact","label":"Contact page","external":false,"blank":false},
        " using the contact form, by emailing ",
        {"href":"mailto:support@researchspectrum.org","label":"support@researchspectrum.org","external":true,"blank":false},
        " directly, or through the official Instagram account ",
        {"href":"https://instagram.com/researchspectrum","label":"@researchspectrum","external":true,"blank":true},
        ". The team responds within 1–2 business days.",
    ],
  },
  {
    id: "faq-q-42",
    dataQ: "What is the support response time? Support responds within 1 to 2 business days.",
    question: "What is the support response time?",
    plain: "The Research Spectrum support team aims to respond to all enquiries within 1–2 business days. More complex issues — such as certificate errors, payment disputes, or technical investigations — may require additional time. When you submit a contact form, you will receive a reference number immediately that can be used to track your request.",
    parts: [
        "The Research Spectrum support team aims to respond to all enquiries within 1–2 business days. More complex issues — such as certificate errors, payment disputes, or technical investigations — may require additional time. When you submit a contact form, you will receive a reference number immediately that can be used to track your request.",
    ],
  },
  {
    id: "faq-q-43",
    dataQ: "Can I contact Research Spectrum through Instagram? Yes for general enquiries and platform updates.",
    question: "Can I contact Research Spectrum through Instagram?",
    plain: "Yes. The official Research Spectrum Instagram account is @researchspectrum and can be used for general enquiries and platform updates. For course-specific support, assignment questions, certificate issues, or technical problems, please use email or the contact form to ensure your request is properly tracked and responded to.",
    parts: [
        "Yes. The official Research Spectrum Instagram account is ",
        {"href":"https://instagram.com/researchspectrum","label":"@researchspectrum","external":true,"blank":true},
        " and can be used for general enquiries and platform updates. For course-specific support, assignment questions, certificate issues, or technical problems, please use email or the contact form to ensure your request is properly tracked and responded to.",
    ],
  },
  {
    id: "faq-q-44",
    dataQ: "Is WhatsApp support available? WhatsApp support is being prepared and is not yet available.",
    question: "Is WhatsApp support available?",
    plain: "WhatsApp support is currently being prepared and is not yet live. Until the channel is available, please contact the team via email at support@researchspectrum.org or through the contact form. You can find updates about WhatsApp availability on the Contact page.",
    parts: [
        "WhatsApp support is currently being prepared and is not yet live. Until the channel is available, please contact the team via email at ",
        {"href":"mailto:support@researchspectrum.org","label":"support@researchspectrum.org","external":true,"blank":false},
        " or through the ",
        {"href":"/contact","label":"contact form","external":false,"blank":false},
        ". You can find updates about WhatsApp availability on the Contact page.",
    ],
  },
  {
    id: "faq-q-45",
    dataQ: "How do I report a technical issue with the platform? Submit a technical issue report through the contact form with device browser and error details.",
    question: "How do I report a technical issue?",
    plain: "Report technical issues through the Contact page using the \"Technical Issue\" category. Include your device type, browser and version, the steps that led to the issue, the exact error message if one appears, and a screenshot if possible. The more detail you provide, the faster the technical team can investigate and resolve the problem.",
    parts: [
        "Report technical issues through the ",
        {"href":"/contact","label":"Contact page","external":false,"blank":false},
        " using the \"Technical Issue\" category. Include your device type, browser and version, the steps that led to the issue, the exact error message if one appears, and a screenshot if possible. The more detail you provide, the faster the technical team can investigate and resolve the problem.",
    ],
  },
  {
    id: "faq-q-46",
    dataQ: "Where can I verify a Research Spectrum certificate? On the Certificate Verification page using the credential ID.",
    question: "Where can I verify a Research Spectrum certificate?",
    plain: "Certificate verification is available at the Certificate Verification page. Enter the credential ID printed on the certificate document and the system will instantly confirm whether the certificate is genuine, display the certificate holder's name, the course, the issue date, and the current status. Verification requires no login and is publicly accessible.",
    parts: [
        "Certificate verification is available at the ",
        {"href":"/verify","label":"Certificate Verification page","external":false,"blank":false},
        ". Enter the credential ID printed on the certificate document and the system will instantly confirm whether the certificate is genuine, display the certificate holder's name, the course, the issue date, and the current status. Verification requires no login and is publicly accessible.",
    ],
  },
]
