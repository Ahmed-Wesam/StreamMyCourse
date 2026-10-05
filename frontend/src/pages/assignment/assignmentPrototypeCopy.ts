/** Static prototype copy from Assignment.html (no API backing). */

export const BRIEF_DELIVERABLES = [
  'Completed research proposal document (.docx or .pdf)',
  'Research question and hypothesis statement (PICO/PECO)',
  'Sampling plan with justification',
  'Ethics & informed consent considerations',
] as const

export const BRIEF_OBJECTIVES = [
  'Formulate a clear, testable research question',
  'Select an appropriate research design for the scenario',
  'Justify a sampling strategy for the target population',
  'Address ethical considerations in study design',
] as const

export const ASSIGNMENT_RESOURCE_CARDS = [
  {
    name: 'Assignment Instructions',
    desc: 'Complete step-by-step guide covering all tasks, formatting requirements, and submission checklist.',
    action: 'Download PDF',
  },
  {
    name: 'Scenario Brief',
    desc: 'A real-world research scenario you will use as the basis for your proposal.',
    action: 'Download PDF',
  },
  {
    name: 'Proposal Template',
    desc: 'Microsoft Word template with pre-formatted proposal sections including research question, study design, sampling, and ethics.',
    action: 'Download .docx',
  },
  {
    name: 'Example Submission',
    desc: 'Annotated example showing a high-scoring submission for a different dataset. Study the structure and format.',
    action: 'Download PDF',
  },
  {
    name: 'Grading Rubric',
    desc: 'Full rubric with criteria descriptions, weightings, and the scoring breakdown for each category.',
    action: 'Download PDF',
  },
] as const

export const ASSIGNMENT_CHECKLIST_ITEMS = [
  {
    title: 'All required deliverables included',
    detail: 'Proposal document submitted as PDF or DOCX',
  },
  {
    title: 'Research question clearly stated',
    detail: 'PICO/PECO framework applied and the question is answerable',
  },
  {
    title: 'Study design selected and justified',
    detail: 'Design choice is explained with a methodological rationale',
  },
  {
    title: 'Sampling strategy explained',
    detail: 'Target population identified, sampling method and feasibility addressed',
  },
  {
    title: 'Ethical considerations addressed',
    detail: 'Consent process described and practical feasibility demonstrated',
  },
  {
    title: 'File formatted and named correctly',
    detail: 'Uploaded as PDF or DOCX, file size under 100 MB',
  },
] as const

export const ASSIGNMENT_FAQ_ITEMS = [
  {
    q: 'Can I resubmit my research proposal if it does not pass?',
    a: 'Yes. Research Spectrum uses mastery-based assessment. If your research proposal receives a revision request, you will receive detailed evaluator feedback explaining what to improve. You may then revise your work and resubmit. There is no limit on the number of revisions, and you will receive written feedback on every submission.',
  },
  {
    q: 'How long does grading take?',
    a: 'Submissions are typically assigned to an evaluator within 24–48 hours of receipt. The review itself takes 3–5 business days depending on evaluator availability and submission complexity. You can track the exact stage of your submission using the Evaluator Status tracker on this page, which updates as your submission moves through the workflow.',
  },
  {
    q: 'What score is required to pass the assignment?',
    a: 'A rubric score of 70% or higher is required to pass the final assignment. The grading rubric evaluates competency areas aligned with your course assignment criteria. You can download the full rubric from the Resources section above.',
  },
  {
    q: 'Can I upload multiple files in my submission?',
    a: 'The submission portal accepts one primary file per submission (PDF, DOCX, or other supported types). If you need to include many files, zip them into a single archive first.',
  },
  {
    q: 'What happens if revisions are requested?',
    a: 'If your submission does not meet the passing threshold, you will receive detailed written feedback. Review this feedback carefully, revise your work accordingly, and resubmit through the same submission portal.',
  },
  {
    q: 'When do I receive my certificate after passing?',
    a: 'Your course certificate is issued when your assignment receives a passing evaluation. It will appear in your Certificates page and on your Dashboard. The certificate includes a unique verification code.',
  },
] as const
